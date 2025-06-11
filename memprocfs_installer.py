import subprocess as sp
import os
import ctypes.util
import logging
from xml.etree import ElementTree as ET
import shutil


logging.basicConfig(level=logging.INFO, format="%(message)s")

try:
    PYTHON_INCLUDE = os.path.join(os.path.dirname(ctypes.util.find_library('python39')), 'include')
    PYTHON_LIB = os.path.join(os.path.dirname(ctypes.util.find_library('python39')), 'libs')
except TypeError:
    logging.error("Python 3.9 not found, please ensure it is installed and accessible.")
    exit(1)

WINDOWS_SDK_DEBUG = "D:\\Windows Kits\\10\\Debuggers\\x64"
MEMPROCFS_REPO = "https://github.com/ufrisk/MemProcFS.git"
LEECHCORE_REPO = "https://github.com/ufrisk/LeechCore.git"
VMMPYC_PROJECT = "vmmpyc.vcxproj"


def change_include_lib_path(project_file):
    ET.register_namespace("", "http://schemas.microsoft.com/developer/msbuild/2003")
    
    tree = ET.parse(project_file)
    root = tree.getroot()
    ns = {"ns": "http://schemas.microsoft.com/developer/msbuild/2003"}

    condition = "'$(Configuration)|$(Platform)'=='Debug|x64'"
    
    for prop_group in root.findall(".//ns:PropertyGroup[@Condition]", ns):
        if prop_group.attrib.get("Condition") == condition:
            include_path = prop_group.find("ns:IncludePath", ns)
            if include_path is not None:
                include_path.text = f"{include_path.text}{PYTHON_INCLUDE}"
                logging.info(f"[+] New IncludePath: {include_path.text}")

            library_path = prop_group.find("ns:LibraryPath", ns)
            if library_path is not None:
                library_path.text = f"{library_path.text}{PYTHON_LIB}"
                logging.info(f"[+] New LibraryPath: {library_path.text}")

    tree.write(project_file, encoding="utf-8", xml_declaration=True)


def git_clone(repo, out_dir):
    repo_name = os.path.basename(repo).replace(".git", "")
    target_path = os.path.join(out_dir, repo_name)

    if not os.path.exists(target_path):
        cmd = ["git", "clone", repo, target_path]
        output = sp.check_output(cmd, stderr=sp.STDOUT)
        logging.info(output.strip().decode())
        logging.info(f"[+] Cloned {repo_name} to {target_path}")
    else:
        logging.info(f"[+] {repo_name} already exists, skipping clone.")

def apply_patch(patch_file, target_dir):
    if os.path.exists(patch_file):
        cmd = ["git", "apply", patch_file]
        output = sp.check_output(cmd, cwd=target_dir, stderr=sp.STDOUT)
        logging.info(output.strip().decode())
    else:
        logging.warning(f"[!] Patch file {patch_file} not found.")


def copy(src, dst):
    if os.path.isdir(src):
        if not os.path.exists(dst):
            shutil.copytree(src, dst)
        else:
            logging.info(f"[+] Directory {dst} already exists, skipping copy.")
    else:
        shutil.copy(src, dst)


def build_memprocfs(build_dir="build"):
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    git_clone(MEMPROCFS_REPO, build_dir)
    git_clone(LEECHCORE_REPO, build_dir)

    project_file = os.path.join(build_dir, "MemProcFS", "vmmpyc", VMMPYC_PROJECT)
    project_file = os.path.abspath(project_file)
    
    if os.path.exists(project_file):
        change_include_lib_path(project_file)
    else:
        logging.warning(f"[!] Project file {project_file} not found.")

    patch_file = "lsass_dump.patch"
    patch_target = os.path.join(build_dir, "MemProcFS")
    patch_target = os.path.abspath(patch_target)
    
    copy(patch_file, patch_target)
    
    patch_file = os.path.join(patch_target, patch_file)
    patch_file = os.path.abspath(patch_file)
    
    apply_patch(patch_file, patch_target)

    # Restore the solution
    cmd = ["dotnet", "restore"]
    output = sp.check_output(cmd, cwd=patch_target, stderr=sp.STDOUT)
    logging.info(f"[+] Restore output:\n{output.decode()}")
    
    # Build the solution
    cmd = ["msbuild", "MemProcFS.sln", "/p:Configuration=Debug", "/p:Platform=x64"]
    logging.info(f"[+] Building MemProcFS with command: {' '.join(cmd)}")
    try:
        output = sp.check_output(cmd, cwd=patch_target, shell=True, stderr=sp.STDOUT)
        logging.info(f"[+] Build output:\n{output.decode()}")
    except sp.CalledProcessError as e:
        logging.error(f"[!] Build failed:\n{e.output.decode()}")

    if os.path.exists(WINDOWS_SDK_DEBUG):
        for dll in os.listdir(WINDOWS_SDK_DEBUG):
            copy(os.path.join(WINDOWS_SDK_DEBUG, dll), os.path.join(build_dir, "MemProcFS", "files"))
    else:
        logging.warning(f"[!] Windows SDK Debug directory {WINDOWS_SDK_DEBUG} not found.")

    logging.info("[+] Done building MemProcFS!")


if __name__ == "__main__":
    build_memprocfs()