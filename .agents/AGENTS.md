# AssetVault Development Rules

1. **Never break existing APIs**.
2. **Keep business logic inside services/**.
3. **API routes should remain thin**.
4. **Database logic stays inside repositories/services**.
5. **Use UUID everywhere**.
6. **In-place library media maintains real disk paths; internal vault uploads use UUID storage paths**.
7. **Every endpoint returns JSON except downloads and media thumbnails**.
8. **Every feature must include typing**.
9. **No placeholder code**.
10. **No TODO comments**.
11. **Every completed task must build successfully before proceeding**.
12. **Finish one task completely before starting the next**.
13. **Prefer simple, maintainable implementations over clever optimizations**.
14. **Always clean up background processes, threads, and filesystem watchers upon application close to prevent orphaned processes**.
15. **Always rebuild and repackage the standalone executable (`build_desktop.py`) upon completing changes so `dist/AssetVault.exe` remains up to date**.

---
**Note for AI Agents**: Refer to [.agents/RELOAD.md](file:///d:/Projects/asset-vault/.agents/RELOAD.md) for quick onboarding, system architecture, start/stop commands, database schemas, and verification workflows.
