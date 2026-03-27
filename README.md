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

- ライブラリのインストール: `pip install -r requirements.txt`
- スクリプトで X API の認証情報を対話的に保存: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\tomii\OneDrive\atcoder_after_contest_bot\save_x_api_secrets.ps1"`
  - CONSUMER KEY
  - CONSUMER SECRET
  - ACCESS TOKEN
  - ACCESS TOKEN SECRET
- 定期実行をタスクスケジューラに登録: `task_scheduler.cmd`
- 手動実行する場合: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\tomii\OneDrive\atcoder_after_contest_bot\run_bot.ps1"`
