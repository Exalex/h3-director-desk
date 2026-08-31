# Windows 本地部署与 8188 端口说明

## 端口职责

| 地址 | 服务 | 当前状态 |
|---|---|---|
| `http://127.0.0.1:8088/` | H3 Director Desk 控制台 | 本机可启动 |
| `http://127.0.0.1:8188/` | ComfyUI/H3 生成服务 | 需要单独安装并启动 |

`director/serve.py` 只负责导演台 Web 服务，不会自动安装、下载模型或启动 ComfyUI。仓库也不包含 ComfyUI 本体、H3 模型权重和完整项目素材。

## 当前机器检查结果

- Windows 本机 `8188` 没有监听进程；
- 未检测到 `nvidia-smi`，当前机器没有可识别的 NVIDIA CUDA 环境；
- 当前代码目录没有 ComfyUI 安装目录；
- 导演台可以在没有 ComfyUI 的情况下打开、编辑项目和运行本地校验；
- 生成、串联和下载视频需要 ComfyUI 在线。

## 远程 GPU 方案

项目原设计是：本机或 spark1 运行导演台，spark2 运行 ComfyUI/H3。远程机器先启动 ComfyUI，并监听 `127.0.0.1:8188`，然后从控制机建立 SSH 隧道：

```bash
ssh -f -N -L 8188:127.0.0.1:8188 exalex@192.168.3.153 \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=30
```

隧道建立后，在控制机访问 `http://127.0.0.1:8188/`；导演台保持使用：

```powershell
python director\serve.py --host 127.0.0.1 --port 8088 --comfy http://127.0.0.1:8188
```

如果 SSH 报 `Permission denied (publickey,password)`，需要先把本机 SSH 公钥加入远程账号，或由管理员在远程机器直接启动 ComfyUI。当前检查中远程 SSH 端口可达，但账号认证未通过，远程 `8188` 也未监听。

## 无 GPU 时的可用范围

没有 ComfyUI 时仍可以：

- 打开导演台；
- 创建和编辑项目；
- 运行分镜质量检查；
- 编译 H3 提示词；
- 查看硬件规划。

不能在当前无 CUDA 环境下完成实际 H3 视频生成。不要用一个空的 8188 模拟服务替代 ComfyUI，否则只能让页面显示在线，无法执行生成工作流。
