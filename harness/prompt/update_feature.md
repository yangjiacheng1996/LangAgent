# feature提示词更新
- 顶层设计：`harness/architecture`中是我对nanomind智能体的顶层设计。
- feature排班表：根据顶层设计，我需要拆解成若干个feature，feature开发有先后顺序。所以我设计了一个feature开发排班表，`harness/feature/README.md`。
- feature开发提示词：根据排班表，为每个feature撰写提示词，以markdown文件的形式存放于`harness/feature`，这样我调用/speckit.specify +feature提示词就能精准开发。

因为feature排班表和所有feature提示词的写作时间是 在顶层设计（specs/001-top-level-design）之后，而在适配器共享基座（specs/002-adapter-shared-infra）之前。feature提示词过于陈旧，可能无法适配新开发的feature。

现在`specs/004-schemas-catalog`已经开发完成了，马上准备开发 005_adapter_middleware_layer 。
所以需要你检查并更新`harness/feature/005_adapter_middleware_layer.md`的内容，以适配已有feature的代码和spec设计文档。