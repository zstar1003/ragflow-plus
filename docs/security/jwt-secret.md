# Management authentication configuration / 管理后台认证配置

管理后台现在必须配置至少 32 字节、每个部署独有的随机 JWT 签名密钥，以及至少 12 个字符的非默认管理员密码。缺失、过短或使用默认/占位值时，后台会拒绝启动。升级已有部署时必须替换已公开的默认密钥和默认管理员密码，部署更新后的后台镜像并重新创建容器；所有旧登录令牌将失效，用户需要重新登录。

## New installations

1. Generate a unique secret locally using a cryptographically secure generator:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. Set `MANAGEMENT_JWT_SECRET` to that output and set `MANAGEMENT_ADMIN_PASSWORD` to your own unique password of at least 12 characters in your deployment's private configuration:
   - CPU/GPU Docker Compose: `docker/.env` (or an exported environment variable).
   - Standalone management Compose: `management/.env` (or an exported environment variable).
   - Running `management/server/app.py` directly: export the variable, or set it in `docker/.env`.

   The example `.env` files intentionally contain no usable JWT key or administrator password. Choose an administrator password using a password manager or a long, unique passphrase. The validator imposes no uppercase, digit, symbol or maximum-length requirement; valid existing non-default passwords of at least 12 characters can be retained. Recognizable default/example passwords are rejected, and whitespace padding does not satisfy the minimum length. Do not use the JWT key as your password. Do not commit your real credentials or share them in logs, issues or screenshots. Keep the JWT key stable across restarts and use the same key for all replicas of one deployment. Do not reuse it across unrelated deployments.

3. Start the updated backend. Compose rejects either missing/empty credential; the backend also rejects JWT keys shorter than 32 UTF-8 bytes, administrator passwords shorter than 12 characters, and recognizable defaults/placeholders. An existing environment variable takes precedence over `.env`, including an empty or invalid value (which causes startup to fail).

## Existing deployment migration

- The previously shipped administrator password is public and must not be reused. Configure your own `MANAGEMENT_ADMIN_PASSWORD` before deploying this update. Existing non-default passwords meeting the requirements need not be changed.
- Previously shipped JWT secrets are public and must not be reused. Generate and persist a fresh, unique secret using the steps above. Do not pad or repeat an old key to meet the length requirement.
- Deploy backend code/images containing this fix. Merging or pulling source code alone does not update a running container: the main CPU/GPU Compose files reference published images. Build an updated backend image using the [image build instructions](../build/README.md), or use a release known to contain the fix, and set `RAGFLOWPLUS_MANAGEMENT_SERVER_IMAGE` to that image. For standalone management Compose, rebuild the backend from the updated source.
- Recreate every management backend container so it receives the new configuration and updated image. For the CPU deployment, after the image, JWT secret and administrator password are configured:

  ```bash
  docker compose --env-file docker/.env -f docker/docker-compose.yml up -d --force-recreate management-backend
  ```

  Use `docker/docker-compose_gpu.yml` for GPU deployments. For standalone management, run `docker compose --env-file management/.env -f management/docker-compose.yml up -d --build --force-recreate management-backend` after preparing the documented model build inputs.
- Replacing the key invalidates all existing management login tokens. Everyone must sign in again. Replace all backend replicas together to avoid accepting old tokens or intermittent authentication failures.
- Changing only the administrator password does not revoke existing JWTs. Rotate `MANAGEMENT_JWT_SECRET` as well when existing sessions must be invalidated.
- This source change does not rotate credentials or deploy any running service automatically. Administrators must carry out the migration. Future key rotations use the same procedure and also invalidate existing tokens.
