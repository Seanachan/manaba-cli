# Google カレンダー同期

[English](README.md) | 日本語

manaba の新しい締切を毎日 Google カレンダーに登録するジョブです。macOS 専用です。

毎日決まった時刻に launchd が [Claude Code](https://docs.claude.com/en/docs/claude-code) をヘッドレスで起動します。
Claude は `manaba todo --days 90` で 90 日以内が締切の課題を取得し、カレンダーにまだない課題だけを `manaba show` で読んで、締切ごとに予定を 1 件作ります。
それより先の締切は、90 日以内に入った時点で登録されます。

- 予定は締切の 15 分前に始まり、締切に終わります。
- リマインダーは 1 日前と 3 時間前です。
- 場所には課題の URL、説明には提出物の要点が入ります。

```text
$ tail ~/Library/Logs/manaba-calendar-sync.log
=== 2026-10-22 22:00:01
CREATED 2
- 10/25 23:55 サンプル講義 第2週レポート(manaba)
- 10/29 10:10 サンプル演習 小テスト(manaba)
SKIPPED (already in calendar) 5
exit=0
```

実行のたびに `CREATED` の行が macOS の通知に出ます。

## インストールの前に：Mac の外に出るデータ

manaba-cli 本体が通信するのは manaba と大学のログインページだけです。この連携は違います。課題の一覧と、新しい課題のページ本文を
**Anthropic**（Claude）に送り、**Google カレンダー**に予定を書き込みます。それでよい場合だけインストールしてください。

## ジョブにできること・できないこと

実行のたびに 3 つの制限がかかります。

1. **ツール：** ジョブは `--permission-mode dontAsk` で動きます。下の表にないツールは、誰にも確認せずに Claude Code が拒否します。
2. **カレンダーの操作：** フック（`guard.sh`）がカレンダーの操作を実行前に毎回確認します。許可するのは選んだカレンダーと、予定に必要な項目だけです（ゲスト、添付ファイル、Meet リンクは不可）。manaba のページに何が書かれていても、Claude が誰かを招待したり、ほかのカレンダーを読んだりすることはできません。
3. **自分の設定は使わない：** ジョブは自分専用の設定（`--setting-sources project` と `settings.json`）だけを読み込みます。あなたの CLAUDE.md、フック、プラグインはジョブの中では動きません。

| できる | できない |
|---|---|
| `manaba todo`、`manaba show`（どちらも読み取り専用） | それ以外のシェルコマンド、ファイル編集、Web アクセス |
| 選んだカレンダーの予定の一覧と作成 | ほかのカレンダー、ゲスト、添付ファイル、予定の変更・削除 |

1 回の実行が `--budget`（既定 1 USD）を超えそうになると止まります。使用量は Claude のプランから引かれます。

## 動作環境

| | |
|---|---|
| macOS | スケジュールに launchd を使います |
| manaba-cli | インストール済みで、`manaba login --set-credentials` で一度ログインしていること。保存したパスワードで、セッションが切れたときにジョブが自分で再ログインします。SSO に多要素認証がある場合、ジョブは自動でログインできません。 |
| Claude Code | インストール済みで、claude.ai アカウント（Pro、Max、Team、Enterprise）でログインしていること。API キーでのログインではコネクタを使えません。 |
| Google カレンダーのコネクタ | claude.ai の **コネクタ** で接続済みであること |

Claude Code からカレンダーが見えるか確認します。

```sh
claude -p "List my Google calendars with their ids" \
  --allowedTools mcp__claude_ai_Google_Calendar__list_calendars
```

## インストール

1. **カレンダーを選びます。** メインのカレンダーなら `primary`、それ以外は上のコマンドで出たカレンダー ID を使います。
   Google カレンダーの **設定 → （カレンダー名）→ カレンダーの統合 → カレンダー ID** でも確認できます。
2. **ファイルを取得します。**
   ```sh
   git clone https://github.com/Seanachan/manaba-cli.git
   cd manaba-cli/integrations/calendar-sync
   ```
3. **インストールします。**
   ```sh
   ./install.sh --calendar-id primary --lang ja --time 22:00
   ```
4. **一度だけ今すぐ実行して確認します。** 2 分ほどで通知が出ます。
   ```sh
   launchctl kickstart gui/$(id -u)/io.github.seanachan.manaba-calendar-sync
   tail ~/Library/Logs/manaba-calendar-sync.log
   ```

| オプション | 既定値 | 意味 |
|---|---|---|
| `--calendar-id ID` | 必須 | 書き込むカレンダー（`primary` はメインのカレンダー） |
| `--lang ja\|en` | `ja` | 予定のタイトルと説明の言語 |
| `--time HH:MM` | `22:00` | 毎日の実行時刻（24 時間表記） |
| `--model NAME` | `sonnet` | ジョブに使う Claude のモデル |
| `--budget USD` | `1` | 1 回の実行の上限額 |
| `--dry-run` | | 一時フォルダにファイルを書き出して場所を表示するだけで、インストールはしない |

設定を変えるときは、新しいオプションで `install.sh` をもう一度実行します。

## 新しい課題の判定方法

ジョブは `manaba todo` を含む予定をカレンダーから検索し、その場所と説明に課題の ID（`_report_2001`、`_query_3002` など。直後に数字が続くものは別の ID とみなします）があるかを見ます。
ID がどれかの予定に入っていれば、その課題は飛ばします。1 件の予定で複数の課題をまとめることもできます。
この照合は Claude 自身が行うため、まれに同じ予定を 2 件作ることがあります。そのときは 1 件を消してください。

そのため、次の 2 点に注意してください。

- 作られた予定の説明の **最後の行**（`確認：manaba todo --course …`）を消さないでください。消すと検索に引っかからず、同じ予定がもう一度作られます。
- `manaba todo` と課題の URL を含めれば、**自分で作った予定** も登録済みとして扱われます。複数の課題の URL を 1 件の説明に貼れば、まとめて 1 件にできます。

ジョブは予定を追加するだけです。先生が締切を変えても予定は動かさず、提出済みの課題の予定も消しません。

## 実行のタイミング

launchd が設定した時刻にジョブを起動します。その時刻に Mac がスリープしていれば、起きたときに実行します。
電源が切れていればその日の分は飛ばされますが、次の実行で未提出の課題をすべて確認するので取りこぼしはありません。

## ファイル

| パス | 内容 |
|---|---|
| `~/.local/share/manaba-calendar-sync/` | `prompt.md`（ジョブへの指示）、`run.sh`、`guard.sh`（カレンダー操作の確認）、`settings.json`（確認を読み込む設定）、`config.env` |
| `~/Library/LaunchAgents/io.github.seanachan.manaba-calendar-sync.plist` | スケジュール |
| `~/Library/Logs/manaba-calendar-sync.log` | 実行ごとの記録 |

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `FAILED: … Not logged in` | `manaba login --headed` を一度実行します。パスワードを変えた場合は `manaba login --set-credentials` も。 |
| コネクタのエラーで `FAILED: exit 1` | claude.ai で Google カレンダーをつなぎ直し、上の確認コマンドをもう一度実行します。 |
| 通知が出ない | システム設定 → 通知 で **スクリプトエディタ** の通知を許可します。 |
| ログに `blocked by manaba-calendar-sync guard` | Claude が制限外のカレンダー操作をしようとしました（ページの文面に誘導されたことが多い）。その操作は実行されていません。普通の課題で起きる場合は、その行を添えて issue を開いてください。 |
| ログに `skipped: another sync is running` | 2 つの実行が重なりました（手動実行と定時実行など）。後の方は何もせずに終わっています。 |
| `install.sh` で `error: a sync is running right now` | 実行が終わるまで 2 分ほど待ち、もう一度 `install.sh` を実行します。 |
| 同じ予定が 2 件できた | 説明から `manaba todo` の行か課題の URL が消えています。1 件を消して、その行を戻してください。 |
| 設定した時刻に何も起きない | `launchctl print gui/$(id -u)/io.github.seanachan.manaba-calendar-sync` で状態と最後の終了コードを確認します。 |

## アンインストール

```sh
./uninstall.sh
```

ジョブを止めて、インストールしたファイルを削除します。ログは `~/Library/Logs/` に残ります。
