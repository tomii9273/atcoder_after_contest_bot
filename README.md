# AtCoder After Contest Bot

[AtCoder](https://atcoder.jp/) で、コンテスト後に問題にテストケースが追加された場合に告知する X (旧 Twitter) bot です。  
https://x.com/AfterContestBot

## プルリクエストについて

機能・コードに大幅な変更・拡張を加えるプルリクエストは、マージしない場合があります。

## ライセンス

MIT License

## 関連リンク

- 作成者 X (旧 Twitter): https://x.com/Tomii9273
- AtCoder: https://atcoder.jp

## 使用方法 (作成者用)

Windows 10/11 に対応

- 以下はリポジトリ直下で実行
- ライブラリのインストール: `pip install -r requirements.txt`
- スクリプトで X API の認証情報を対話的に入力 → 暗号化してローカルに保存: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\save_x_api_secrets.ps1"`
  - CONSUMER KEY
  - CONSUMER SECRET
  - ACCESS TOKEN
  - ACCESS TOKEN SECRET
- 以下を実行する前に Firefox で AtCoder にログインしておく必要あり
- 定期実行をタスクスケジューラに登録 (時刻表記は PC のローカル時間で): `task_scheduler.cmd`
  - 同名のタスクを時間や頻度を変えて登録すると、前のタスクは消える。
  - 時間になると PowerShell が立ち上がるが、右クリックなどで選択状態にすると一時停止するので注意
- 手動実行する場合: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\run_bot.ps1"`
