# 项目目录约定

导演台把 `projects/` 下每个包含 `project.json` 的目录视为一个独立项目，
把项目里的每个 `episodes/*/episode.json` 视为一集。

```text
projects/<project>/
  project.json
  assets/       跨集共享的场景图和项目素材
  episodes/<episode>/
    episode.json  本集的简案、角色、场景和分镜
    assets/       本集场景素材
    references/   本集角色卡、参考图
    prompts/      本集编译后的 H3 提示词
    outputs/      本集生成的视频和装配结果
```

左侧先切换项目，再切换集数。工作台中央和右侧制作计划始终绑定当前
`episode.json`，素材路径必须指向当前项目/集数目录。`outputs/` 中的生成
结果默认不进入 Git。
