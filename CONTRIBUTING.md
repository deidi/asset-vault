# Contributing to AssetVault

Thank you for your interest in contributing to **AssetVault**! We welcome bug reports, feature suggestions, documentation improvements, and code contributions.

---

## 🛠️ Development Setup

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 20+** and `npm`
- **Git**

### 2. Clone the Repository
```bash
git clone https://github.com/deidi/asset-vault.git
cd asset-vault
```

### 3. Backend Setup
```bash
# Create and activate virtual environment
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1   # On Windows

# Install Python dependencies
pip install -r backend/requirements.txt
pip install pyinstaller
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev   # Starts Vite development server
```

---

## 🧪 Running Automated Tests

Before submitting changes, ensure the entire test suite passes:

```bash
# Run all backend unit and integration tests
.\backend\.venv\Scripts\python.exe tests/run_tests.py
```

---

## 📦 Building the Desktop Application

To package the standalone Windows executable:

```bash
.\backend\.venv\Scripts\python.exe build_desktop.py
```
The output binary will be created at `dist/AssetVault.exe`.

---

## 📐 Code Architecture Guidelines

Please adhere to our Clean Architecture principles:
1. **Never break existing APIs**.
2. **Keep business logic inside `backend/app/services/`**; route handlers in `backend/app/routes/` should remain thin.
3. **Database logic** stays in `backend/app/repositories/` and `app/models/`.
4. **Use UUID primary keys** across all database entities.
5. **In-place library media** must maintain real absolute disk paths.
6. **Always ensure background file watchers and threads** are cleaned up gracefully upon shutdown.

---

## 🔄 Submitting a Pull Request

1. **Fork the repository** and create your branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** with clear, descriptive commit messages.
3. **Run the test suite** (`python tests/run_tests.py`) to verify zero regressions.
4. **Push your branch** to your fork and open a Pull Request against `main`.
5. Describe your changes clearly using the PR template.

Thank you for making AssetVault better for everyone!
