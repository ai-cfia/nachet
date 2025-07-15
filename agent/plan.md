# Plan: Converting Nachet Backend to UV Project

## Current State Analysis

### Existing Structure

- Uses `requirements.txt` with 16 dependencies including git-based `nachet-datastore`
- Has local `ailab-datastore` library in `lib/` directory (with existing pyproject.toml files)
- Multiple requirements files (requirements.txt, requirements.txt.local, requirements2025031201.txt)
- Standard Python Quart web application with Azure integration

### Dependencies Analysis

```
nachet-datastore @git+https://github.com/ai-cfia/ailab-datastore.git@231-split-nachet-config-secrets
numpy==1.26.4
azure-storage-blob
azure-identity
flask==3.0.3
quart==0.19.6
quart-cors
python-dotenv
hypercorn
Pillow==10.3.0
cryptography
pyyaml
pydantic==2.7.1
pydantic-core==2.18.2
python-magic
PyJWT
```

### Updated Dependency Configuration

```Text
nachet-datastore @git+https://github.com/ai-cfia/nachet.git@v1.1.0-nachet-datastore
```

## Conversion Plan

### Phase 1: Core uv Project Setup

1. **Create main pyproject.toml**
   - Convert requirements.txt to modern pyproject.toml format
   - Define project metadata (name, version, description, authors)
   - Set up proper dependency specifications

2. **Handle git dependency**
   - Configure the `nachet-datastore@git+https://github.com/ai-cfia/nachet.git@v1.1.0-nachet-datastore` dependency properly in pyproject.toml
   - Use tag `v1.1.0-nachet-datastore` for stable versioning

3. **Define project metadata**
   - Name: `nachet-backend`
   - Version: Extract from existing documentation
   - Description: "Canadian government (CFIA) AI-powered seed identification system backend"
   - Authors: Based on existing documentation

### Phase 2: Workspace Configuration (Optional)

1. **Evaluate workspace structure**
   - Consider making this a uv workspace with local `ailab-datastore` as a workspace member
   - Analyze pros/cons of workspace vs git dependency

2. **Update ailab-datastore integration**
   - Decision point: git dependency vs local workspace dependency
   - Consider impact on development workflow

### Phase 3: Build & Development Environment

1. **Update Dockerfile**
   - Modify both `Dockerfile` and `Dockerfile.local` to use `uv` instead of `pip`
   - Update build stages for uv installation and dependency management
   - Ensure proper caching layers

2. **Update documentation**
   - Change CLAUDE.md commands from `pip install -r requirements.txt` to `uv sync`
   - Update README.md with new development setup instructions
   - Update any other documentation referencing pip

3. **Development scripts**
   - Ensure all development workflows use uv
   - Update any shell scripts or automation

### Phase 4: Migration & Cleanup

1. **Backup existing setup**
   - Keep requirements.txt temporarily for rollback capability
   - Document rollback procedure

2. **Clean up redundant files**
   - Remove old requirements files once conversion is verified
   - Clean up any pip-related configurations

3. **Update CI/CD**
   - Any GitHub Actions or deployment scripts
   - Update deployment documentation

## Key Decisions Needed

### 1. Workspace vs Single Project

- **Option A**: Use uv workspace to include local ailab-datastore
  - Pros: Better local development, unified dependency management
  - Cons: More complex setup, potential CI/CD changes

- **Option B**: Keep git dependency
  - Pros: Simpler migration, minimal changes
  - Cons: Continues external dependency complexity

### 2. Version Pinning Strategy

- **Current**: Exact pins for some packages (numpy==1.26.4, flask==3.0.3)
- **Options**:
  - Keep exact pins for stability
  - Use more flexible constraints for easier updates
  - Mixed approach (pin critical packages, flexible for others)

### 3. Development Dependencies

- **Current**: All dependencies in single requirements.txt
- **Proposed**: Separate dev dependencies (testing, linting) from production
- **Benefits**: Cleaner production builds, better dependency management

## Implementation Steps

1. [ ] Create initial pyproject.toml
2. [ ] Test basic uv sync functionality
3. [ ] Update Dockerfiles
4. [ ] Update documentation
5. [ ] Test full application startup
6. [ ] Update CI/CD if needed
7. [ ] Create migration guide for team
8. [ ] Clean up old files

## Rollback Plan

- Keep requirements.txt until full verification
- Document exact pip commands for rollback
- Maintain Docker image tags for quick reversion

## Success Criteria

- [ ] Application starts and runs identically to current setup
- [ ] All dependencies properly resolved
- [ ] Docker builds successfully
- [ ] Documentation updated
- [ ] Team can follow migration guide successfully
