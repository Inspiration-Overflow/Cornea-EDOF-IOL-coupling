# Final R8 release pointer — 2026-08-24

本文件用于给 MVP/R8 投稿前冻结状态提供一个简短、可读的 Git 指针说明。

## 科学主线

```text
baseline = MVP_2026_v2
R8 study + final manuscript integration = ef407958303be8736f56b17a8c43de3398343466
submission preflight/status/reference verification = 57e98056a1fac44a8bd02ddb95af3b7fd22f81db
```

## 冻结 ref

```text
release ref = release/mvp-2026-v2-r8-final
```

该 ref 应指向包含本文件的最终 `main` 提交，并作为当前 MVP/R8 投稿包的代码与 evidence 冻结指针。后续科学开发不得在该 ref 上继续推进；新工作应从新的分支开始。

当前 GitHub 连接器不提供 tag/release 创建接口，因此本次使用独立 release branch 作为可由当前环境实际创建并核验的 Git ref。若后续在 GitHub UI/CLI 建立同名正式 tag/release，应指向完全相同的提交 SHA，不应重新生成或改写 R8 evidence。

## 绑定内容

此 ref 绑定：

- R5.2/R6/R7 已接受的 Binary4 模型实现；
- R8 96-config production evidence；
- R8 offline integration evidence；
- `docs/MANUSCRIPT_FINAL_R8_2026-08-22.md`；
- `docs/MANUSCRIPT_R8_SCIENTIFIC_QC_2026-08-22.md`；
- `docs/MANUSCRIPT_R8_FIGURE_TABLE_PLAN_2026-08-22.md`；
- `docs/RMD_EXECUTION_STATUS.md`；
- `docs/MANUSCRIPT_REFERENCE_VERIFICATION_2026-08-24.md`；
- `.github/workflows/offline-quality.yml` 的 `main` push gate。

科学证据边界保持不变：计算研究不是临床验证，`formal_scientific_lock=false` 的离线 evidence 不因建立 release ref 而被改写。
