import os
import sys
import subprocess
import shutil

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    python_exe = os.path.join(root_dir, "backend", ".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    print("=" * 60)
    print("        ASSETVAULT STANDALONE DESKTOP BUILDER        ")
    print("=" * 60)

    # 1. Build Frontend SPA
    print("\n[1/3] Building Frontend SPA...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    npm_res = subprocess.run([npm_cmd, "run", "build"], cwd=frontend_dir)
    if npm_res.returncode != 0:
        print("ERROR: Frontend build failed.")
        sys.exit(1)
    print("[OK] Frontend bundle built successfully in public/")

    # 2. Run Backend Unit & Integration Tests
    print("\n[2/3] Running Python Test Suite...")
    test_runner = os.path.join(root_dir, "tests", "run_tests.py")
    test_res = subprocess.run([python_exe, test_runner], cwd=root_dir)
    if test_res.returncode != 0:
        print("ERROR: Automated tests failed. Aborting build.")
        sys.exit(1)
    print("[OK] All tests passed successfully.")

    # 3. Package Executable with PyInstaller
    print("\n[3/3] Packaging Standalone Application with PyInstaller...")
    spec_file = os.path.join(root_dir, "assetvault.spec")
    pyinstaller_res = subprocess.run([
        python_exe,
        "-m",
        "PyInstaller",
        "--noconfirm",
        spec_file
    ], cwd=root_dir)

    if pyinstaller_res.returncode != 0:
        print("ERROR: PyInstaller packaging failed.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("[OK] PORTABLE STANDALONE EXE BUILD COMPLETE!")
    print(f"  Portable App Location: {os.path.join(root_dir, 'dist', 'AssetVault.exe')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
