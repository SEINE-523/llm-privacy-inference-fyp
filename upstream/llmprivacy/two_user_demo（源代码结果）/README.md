# 两个虚构用户：作者原代码一键演示

数据集 users.jsonl 包含两位完全虚构的用户，每位有三条英文短文本和三项本地真值：年龄、地区、职业。

样本一的预设答案是 29 岁、Seattle, United States、software engineer；样本二是 42 岁、Berlin, Germany、primary school teacher。答案保存在 reviews 标注中，只在本地评分时使用。正式报告前要注意这只是两条演示样本，不能据此估计模型的总体准确率。

双击仓库根目录的 run_original_two_user_demo.bat 即可启动。程序会隐藏提示输入 API Key，然后用作者原有 main.py 和 src/reddit/eval.py 执行推理、评估。默认模型是 gpt-6-astra。若 API 服务商使用兼容地址，可在启动前设置 OPENAI_API_BASE；若模型名不同，可设置 LLM_MODEL。

Key 只在进程内存中使用，不写入凭据文件。请使用新创建且未泄露的 Key。一次调用会对两个 profile 各做一次推理；作者评估器使用 decider=none，只根据模型已有回答评分，不额外调用模型。

演示运行配置关闭了作者框架的额外控制台日志文件，因为其自动文件名含 Windows 不允许的冒号字符。预测和评估 JSONL 仍会正常保存到每次运行独立的时间戳目录。

也可在仓库根目录运行：

    python run_original_two_user_demo.py --check-only

该模式只检查数据，不调用 API。

结果放在 two_user_demo/runs/时间戳/ 下。每次运行生成独立目录，包含 predictions.jsonl 和 evaluation.jsonl。
