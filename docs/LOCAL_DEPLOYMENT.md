# Windows 本地部署与 8188 端口说明

## 端口职责

| 地址 | 服务 | 当前状态 |
|---|---|---|
| `http://127.0.0.1:8088/` | H3 Director Desk 控制台 | 本机可启动 |
| `http://127.0.0.1:8188/` | ComfyUI/H3 生成服务 | 需要单独安装并启动 |

`director/serve.py` 只负责导演台 Web 服务，不会自动安装、下载模型或启动 ComfyUI。当前部署目录包含可切换的 Odyssey 项目 JSON、风格文件和场景素材，但不包含 ComfyUI 本体、H3 模型权重或生成视频。

项目库先按 `projects/<项目目录>/project.json` 切换项目，再按
`episodes/<集数目录>/episode.json` 切换集数。每一集独立保存
`assets/`、`references/`、`prompts/` 和 `outputs/`，切换后工作台不会读取其他
集数的配置和素材。

## 当前机器检查结果

- Windows 本机 `8188` 没有监听进程；
- 未检测到 `nvidia-smi`，当前机器没有可识别的 NVIDIA CUDA 环境；
- 当前代码目录没有 ComfyUI 安装目录；
- 导演台可以在没有 ComfyUI 的情况下打开、编辑项目和运行本地校验；
- 生成、串联和下载视频需要 ComfyUI 在线。

## 5800H 控制 spark1 的 ComfyUI

当前 spark1 已将 spark2 的 ComfyUI 转发到 Wi-Fi 地址
`192.168.3.75:8188`。5800H 上的 Director Desk 直接调用这个地址，不需要
再建立第二层 SSH 隧道：

```text
5800H Director Desk
    -> http://192.168.3.75:8188
spark1 Wi-Fi 192.168.3.75:8188
    -> spark1 到 spark2 的转发
spark2 127.0.0.1:8188 ComfyUI/H3
```

先验证 spark1 的转发：

```powershell
Invoke-WebRequest -UseBasicParsing http://192.168.3.75:8188/system_stats
```

返回 ComfyUI JSON 后，再从本目录双击 `start_local.bat` 启动新版导演台。
导演台调用地址为 `http://192.168.3.75:8188`，不需要在 5800H 安装 H3
模型或 GPU 版 ComfyUI。

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
