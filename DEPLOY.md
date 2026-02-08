# Deployment Checklist

Use this checklist after making changes to ensure nothing is missed.

## After Code Changes

### 1. Testing
- [ ] Run backend tests: `pytest -v`
- [ ] Run e2e tests: `npx playwright test` (requires running server)
- [ ] Check test coverage for new features

### 2. Documentation
- [ ] Add/update docstrings in modified Python files
- [ ] Add/update JSDoc comments in modified JS files
- [ ] Update README if user-facing features changed
- [ ] Update API docs if endpoints changed

### 3. Commit & Push
- [ ] `git add -A`
- [ ] `git commit -m "descriptive message"`
- [ ] `git push`

### 4. Restart Services

**When to restart what:**

| Change Type | Action Required |
|-------------|-----------------|
| Python code (app/) | Restart containers: `docker compose -f docker-compose.local.yml up --build -d` |
| Frontend (frontend/) | Restart containers (static files are copied at build) |
| Docker/Caddy config | Restart containers |
| .env changes | Restart containers |
| requirements.txt | Rebuild containers: `docker compose -f docker-compose.local.yml up --build -d` |
| Database schema | Restart + run migrations (if using Alembic) |
| System packages | Restart droplet (rare) |
| Kernel/OS updates | Restart droplet |

**Quick commands:**

```bash
# Restart containers (rebuilds if needed)
cd /root/projects/eigencore
docker compose -f docker-compose.local.yml up --build -d

# Check status
docker compose -f docker-compose.local.yml ps

# View logs
docker compose -f docker-compose.local.yml logs -f

# Full restart (stop + start)
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml up --build -d

# Restart droplet (only if necessary)
sudo reboot
```

### 5. Verify
- [ ] Check service is running: `docker compose ps`
- [ ] Test a quick API call: `curl http://localhost:8080/health`
- [ ] Test frontend loads: open http://104.248.27.154:8080

## Production Deployment

Additional steps for production:

- [ ] Review changes for security issues
- [ ] Check environment variables are set correctly
- [ ] Verify HTTPS is working
- [ ] Monitor logs for errors after deploy
- [ ] Test critical user flows manually

## Rollback

If something breaks:

```bash
# Check recent commits
git log --oneline -10

# Revert to previous commit
git revert HEAD
git push

# Or reset to specific commit (destructive)
git reset --hard <commit-hash>
git push --force

# Restart
docker compose -f docker-compose.local.yml up --build -d
```
