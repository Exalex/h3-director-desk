# Director Desk + ComfyUI + H3 部署架构

## 结论

5800H 本机放 Director Desk 控制服务和浏览器；局域网 GPU 主机放 ComfyUI、H3 自定义节点、模型权重和实际生成任务。

```text
5800H 本机
  浏览器
      |
  Director Desk :8088
  serve.py（项目/API/任务编排）
      |
      |  SSH 隧道或局域网 HTTP
      v
GPU 主机
  ComfyUI :8188
  MiniMax H3 节点 + 模型权重
  NVIDIA GPU / 显存
      |
      v
  视频、音频、抽帧与生成输出
```

## 三个层级的区别

| 层级 | 组件 | 负责什么 | 应放在哪里 |
|---|---|---|---|
| 制作编排层 | H3 Director Desk | 项目 JSON、分镜、校验、Prompt、任务进度、媒体预览和装配调度 | 5800H 本机 |
| 工作流执行层 | ComfyUI | 解析节点图、加载模型、执行采样、处理首帧/参考图并输出媒体 | GPU 主机 |
| 模型推理层 | MiniMax H3 | 视频与原生音频的实际推理 | GPU 主机的 ComfyUI 进程内 |

Director Desk 不是 H3 模型本身，也不替代 ComfyUI。它通过 ComfyUI 的 HTTP API 提交工作流，并在本地轮询任务、下载结果和保存项目记录。

## 推荐连接方式：SSH 隧道

在 GPU 主机上让 ComfyUI 只监听本机：

```bash
python main.py --listen 127.0.0.1 --port 8188
```

在 5800H 本机建立端口转发：

```bash
ssh -N -L 8188:127.0.0.1:8188 <gpu-user>@<gpu-host-ip>
```

然后在 5800H 本机启动 Director Desk：

```powershell
cd D:\workspace\deepseekSpace\h3-director-desk
python director\serve.py --host 127.0.0.1 --port 8088 --comfy http://127.0.0.1:8188
```

访问：

```text
http://127.0.0.1:8088/
```

这种方式下，`127.0.0.1:8188` 虽然出现在 5800H 上，但它实际通过 SSH 隧道连接到 GPU 主机的 ComfyUI。

## 可选连接方式：直接局域网访问

如果不使用 SSH 隧道，GPU 主机上的 ComfyUI 需要监听局域网地址：

```bash
python main.py --listen 0.0.0.0 --port 8188
```

然后 5800H 本机启动：

```powershell
python director\serve.py --host 127.0.0.1 --port 8088 --comfy http://<gpu-host-ip>:8188
```

这种方式配置简单，但会把 ComfyUI API 暴露给局域网。应限制防火墙只允许局域网网段，禁止端口映射到公网；远程访问和多人环境优先使用 SSH 隧道。

## 文件和任务流

1. 浏览器在 5800H 上编辑项目并保存 JSON。
2. Director Desk 将结构化 Shot 编译为 H3 Prompt 和 ComfyUI 工作流。
3. 本机通过 `8188` 隧道或 GPU 主机 IP 调用 ComfyUI。
4. 首帧/参考图由 Director Desk 上传到 ComfyUI，生成任务在 GPU 主机执行。
5. Director Desk 轮询 `/history`，再通过 `/view` 下载视频到本机输出目录。
6. 本机继续执行项目记录、QC 浏览和最终装配；需要时也可以把输出目录放到共享盘。

## 端口判断

- `8088` 无法访问：Director Desk 没启动，或访问地址/防火墙不对。
- `8188` 无法访问：ComfyUI 没启动、SSH 隧道没建立、远程地址错误或 GPU 主机防火墙阻断。
- `8088` 正常而 `8188` 离线：项目编辑和部分本地校验仍可用，但不能执行 H3 视频生成。

## 当前实测状态（2026-08-31）

已从 5800H 通过 spark1 的导演台接口验证完整的服务连接：

| 检查项 | 结果 |
|---|---|
| spark1 导演台 `192.168.3.75:8088` | 在线，HTTP 200 |
| spark1 Qwen/SGLang `192.168.3.75:8888` | 在线 |
| spark1 → ComfyUI 本地转发 `127.0.0.1:8188` | 导演台报告在线 |
| ComfyUI 版本 | `0.31.0` |
| PyTorch | `2.11.0+cu130` |
| GPU | `NVIDIA GB10`，设备 `cuda:0` |
| GPU 显存 | 总量约 130.7 GB，检测时空闲约 114.3 GB |

直接从 5800H 访问 `spark1:8188` 或 `spark2:8188` 不通是预期现象：ComfyUI 监听 `127.0.0.1:8188`，SSH 隧道终点在 spark1，5800H 只需要访问 `http://192.168.3.75:8088`。本次验证只读取 `/api/director` 和 ComfyUI `/system_stats`，没有提交实际视频生成任务。

## 10 秒生成测试（2026-08-31）

已提交一个独立的单镜头 T2V 测试项目，没有运行正式奥德赛项目，也没有提交整集任务。

| 项目 | 结果 |
|---|---|
| 任务 | `b02f70ae5e` |
| 参数 | `480x832`、243 帧、24fps、seed `42` |
| ComfyUI 任务 | 完成，Director Desk 状态 `done` |
| 输出 | `gen/h3_10s_connectivity_test/S01.mp4` |
| 媒体校验 | H.264、`480x832`、243 帧、`10.125s`、约 `1.0MB` |

这次测试证明了 Director Desk → spark1 转发 → ComfyUI/H3/GPU 的真实生成链路可用。测试项目和视频输出保留在 spark1，便于后续在导演台中预览；正式生成前仍应补齐测试项目的逐秒指令质量门禁。

## 对 5800H 本机的建议

5800H 只承担浏览器、Python 标准库服务、项目 JSON、Prompt 编译、任务轮询和轻量 ffmpeg/QC。不要把 H3 模型权重或 ComfyUI 的 GPU 推理放在这台机器上，除非它另外具备可用的 NVIDIA GPU、CUDA 和足够显存。
