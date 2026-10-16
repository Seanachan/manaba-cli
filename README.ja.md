# manaba-cli

[English](README.md) | 日本語

[![CI](https://github.com/Seanachan/manaba-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Seanachan/manaba-cli/actions/workflows/ci.yml)

多くの日本の大学で使われている授業支援システム [manaba](https://manaba.jp/) を、
コマンドラインから**読み取り専用**で利用するツールです。履修コース、未提出の課題と締切、
コースニュース、コンテンツを一覧でき、任意の manaba ページをテキストとして表示できます。
出力は人向けの表、またはスクリプトや AI エージェント向けの JSON（`--json`）です。

既定の接続先は筑波大学の manaba です。ほかの大学でも設定すれば使えます
（[ほかの大学で使う](#ほかの大学で使う) を参照）。

```text
$ manaba todo --days 7
  Deadline          Course         Kind    Title               Status  Mine
 ─────────────────────────────────────────────────────────────────────────────
  2026-10-18 23:00  Sample Course  report  Week 2 report       open    unsubmitted
  2026-10-20 12:15  Sample Course  drill   Vocabulary drill    open    unsubmitted
```

## 絶対にしないこと

manaba-cli は**読むだけ**です。提出・解答・保存・取り消し・削除など、manaba 上の状態を変える操作は一切行いません。

- manaba へのリクエストはすべて HTTP `GET` です。HTTP セッションのクラスには `POST`・`PUT`・`DELETE` のメソッドがなく、追加するとテストが失敗します。
- manaba には、通常の `GET` で状態が変わるリンクがあります（ログアウト、表示言語の切り替え、お気に入りコースの登録・解除、一覧表示形式の切り替え）。manaba-cli はこれらの URL を、リクエストを送る前に拒否します。
- 送信するフォームは、大学の SSO ログインフォームだけです。手でログインするのと同じように、Playwright を通じて Chrome が送信します。
- 唯一の副作用：記事やページを開くと、ブラウザで開いたときと同じく既読になります。

## 動作環境

| | |
|---|---|
| Python | 3.11 以上 |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | ツールのインストールに使用 |
| Google Chrome | SSO ログインにだけ使用。インストール済みの Chrome を Playwright が操作するので、`playwright install` は不要です |
| システムのキーリング | パスワードの保存先（下表を参照） |

| OS | 状況 | 補足 |
|---|---|---|
| macOS | 主な対象、日常的に使用 | パスワードは macOS キーチェーンに保存されます。確認ダイアログが出たら **常に許可** を選んでください。 |
| Linux | CI で単体テストのみ実行、ログインは未確認 | Secret Service 対応のキーリング（GNOME Keyring または KWallet）をロック解除した状態で用意してください。Google Chrome が必要で、ディストリビューションの Chromium は使われません。 |
| Windows | 未検証 | パスワードは Windows 資格情報マネージャーに保存されます。ファイルのパーミッション（0600）は適用されません。 |

## インストール

```sh
uv tool install git+https://github.com/Seanachan/manaba-cli
manaba --version
```

更新は `uv tool upgrade manaba-cli` で行います。削除は [アンインストール](#アンインストール) を参照してください。

## 初回の設定

```sh
manaba login --set-credentials --headed
manaba status
```

1. `--set-credentials` で manaba（SSO）のユーザー名とパスワードを入力します。パスワードはシステムのキーリングに保存され、ファイルには書き込まれません。
2. `--headed` を付けると、初回ログインの Chrome ウィンドウが表示され、SSO ページが自動で入力されて閉じる様子を確認できます。同意画面や多要素認証など想定外の画面が出た場合は、5 分以内に手で操作を完了してください。
3. `manaba status` で `logged_in  yes` と表示されれば完了です。

以降のコマンドは画面を出さずに動きます。セッションが切れた場合は、次のコマンドが自動で再ログインします（1 回の実行につき最大 1 回）。

## コマンド

すべてのコマンドで `--json` が使えます。JSON のキーは固定で、日時は日本時間の ISO 8601（`+09:00`）です。以下のサンプルは一部を省略しており、データは架空のものです。

### `manaba status`：セッションは有効か

```sh
manaba status --json
```
```json
{"logged_in": true, "base_url": "https://manaba.tsukuba.ac.jp", "username": "s0000000",
 "credentials_stored": true, "cookies_expire_at": null,
 "config_file": "/home/you/.config/manaba-cli/config.toml",
 "cookies_file": "/home/you/.config/manaba-cli/cookies.json"}
```

### `manaba courses`：履修コース一覧

```sh
manaba courses --json
```
```json
[{"id": 1001, "name": "Sample Course", "year": 2026, "period": "Autumn AB Tue. 3",
  "teacher": "Teacher A", "url": "https://manaba.tsukuba.ac.jp/ct/course_1001",
  "flags": {"unread_news": true, "unsubmitted_tasks": true, "new_grades": false,
            "unread_threads": false, "individual_messages": false}}]
```

### `manaba todo`：課題と締切（メインのコマンド）

```sh
manaba todo                    # 全コースの未完了の課題を締切の近い順に表示
manaba todo --days 7           # 7 日以内が締切のものだけ
manaba todo --all              # 提出済み・受付終了の課題も含める
manaba todo --course 1001      # 1 つのコースだけ
```
```json
[{"course_id": 1001, "course_name": "Sample Course", "kind": "report", "id": 2001,
  "title": "Week 2 report", "status": "open", "my_status": "unsubmitted",
  "status_raw": "In progress / Not submitted",
  "start": "2026-10-09T13:30:00+09:00", "deadline": "2026-10-18T23:00:00+09:00",
  "url": "https://manaba.tsukuba.ac.jp/ct/course_1001_report_2001"}]
```

| フィールド | 値 |
|---|---|
| `kind` | `query`（小テスト）、`drill`（ドリル）、`report`（レポート）、`survey`（アンケート） |
| `status` | `upcoming`（受付開始待ち）、`open`（受付中）、`closed`（受付終了）。表記が不明な場合は `null` で、元の文字列が `status_raw` に残ります |
| `my_status` | `unsubmitted`、`submitted`、`passed`、`unpassed`、または `null` |
| `deadline` | ISO 8601。終了日時のない課題は `null` |

「未完了」とは、受付終了でなく、提出済み・合格済みでもない課題のことです。状態が不明な課題も未完了として扱います。

### `manaba news`：コースニュース

```sh
manaba news --since 2026-10-01 --limit 10
```
```json
[{"course_id": 1001, "course_name": "Sample Course", "id": 3001, "title": "Homework and listening task",
  "author": "Teacher A", "posted_at": "2026-10-16T00:00:00+09:00", "unread": true,
  "url": "https://manaba.tsukuba.ac.jp/ct/course_1001_news_3001"}]
```

### `manaba news show`：ニュースを 1 件表示

```sh
manaba news show https://manaba.tsukuba.ac.jp/ct/course_1001_news_3001
manaba news show 3001 --course 1001          # 上と同じ
```
```json
{"course_id": 1001, "id": 3001, "title": "Homework and listening task", "author": "Teacher A",
 "posted_at": "2026-10-16T00:00:00+09:00", "body": "Please submit …",
 "links": [{"text": "Report page", "url": "https://…/ct/course_1001_report_2001"}],
 "attachments": [{"name": "handout.pdf", "uploaded_at": "2026-10-15T17:23:00+09:00", "url": "https://…"}]}
```

### `manaba contents <コース ID>`：コンテンツ（授業資料）

```sh
manaba contents 1001
```
```json
[{"id": "5001c1001", "title": "Class records", "url": "https://…/ct/page_5001c1001",
  "pages": [{"title": "Orientation", "author": "Teacher A", "updated_at": "2026-10-02T11:30:00+09:00",
             "publish_start": null, "publish_end": null, "text": "How the class works …",
             "links": [], "attachments": [{"name": "slides.pdf", "url": "https://…"}]}]}]
```

添付ファイルはリンクとして一覧するだけで、ダウンロードはしません。

### `manaba show <URL>`：任意のページをテキストで表示

```sh
manaba show https://manaba.tsukuba.ac.jp/ct/course_1001_drill_2002
```
```json
{"url": "https://…/ct/course_1001_drill_2002_submitlog_9001", "title": "Vocabulary drill",
 "text": "1. Sample question\n( ) A\n(x) B\nFill in: [answer]",
 "links": [{"text": "Tests", "url": "https://…/ct/course_1001_query"}]}
```

小テストの結果ページでは、自分の解答がフォームの入力欄に入っています。`show` は選んだ選択肢を `(x)`、選ばなかった選択肢を `( )`、記述した解答を `[解答]` と表示します。ドリルや小テストのページにある **Result**（結果）リンクを開くと、自分の解答を確認できます。

### `manaba login`

| オプション | 用途 |
|---|---|
| `--set-credentials` | ユーザー名とパスワードを入力して保存します。 |
| `--headed` | Chrome のウィンドウを表示します。デバッグや、多要素認証を手で完了するときに使います。 |

グローバルオプションはコマンドの前に付けます。`manaba --debug todo` は、リクエストの URL（クエリ文字列は除去）とステータスコードを標準エラー出力に記録します。`manaba --version` はバージョンを表示します。

### 終了コード

| コード | 意味 |
|---|---|
| 0 | 成功 |
| 1 | その他のエラー：ネットワーク、存在しないコース、manaba 以外の URL、状態を変えるリンクの拒否、キーリングが使えない |
| 2 | 未ログイン、または SSO ログインの失敗 |
| 3 | ページを解析できなかった（[トラブルシューティング](#トラブルシューティング) を参照） |

## 設定

| 項目 | 場所 |
|---|---|
| 設定ファイル | `~/.config/manaba-cli/config.toml`（キーは `base_url` と `username`） |
| セッション Cookie | `~/.config/manaba-cli/cookies.json`（ファイルは 0600、ディレクトリは 0700） |
| パスワード | システムのキーリング、サービス名 `manaba-cli` |
| 解析エラー時の保存先 | `~/.cache/manaba-cli/last-error.html` |
| 環境変数での上書き | `MANABA_BASE_URL`、`MANABA_USERNAME`、`XDG_CONFIG_HOME`、`XDG_CACHE_HOME` |

```toml
# ~/.config/manaba-cli/config.toml
base_url = "https://manaba.tsukuba.ac.jp"
username = "s0000000"
```

## ほかの大学で使う

manaba はどの大学でも同じ製品なので、ページの解析処理は共通です。大学ごとに異なりうるのは、サイトの URL と SSO のログインページの 2 点です。

1. **接続先を設定する。** `config.toml` の `base_url` を設定するか、`MANABA_BASE_URL=https://manaba.example-u.ac.jp` を環境変数で指定します。`/ct/` より前の部分を指定してください。
2. **ログインを確認する。** `manaba --debug login --set-credentials --headed` を実行し、ウィンドウの動きを見ます。
   - ログインできれば完了です。
   - ログインフォームで止まる場合は、IdP の入力欄の名前が異なります。セレクタは [`src/manaba_cli/auth.py`](src/manaba_cli/auth.py) の冒頭にある 3 つの定数です。

     ```python
     USERNAME_FIELD = "input[name=j_username]"
     PASSWORD_FIELD = "input[name=j_password]"
     PROCEED_BUTTON = "button[name=_eventId_proceed], input[type=submit][name=_eventId_proceed]"
     ```

     これは Shibboleth IdP v3 以降の既定値です。自分の大学のログインページでユーザー名欄・パスワード欄・ログインボタンを調べ、セレクタを合わせてください。既定値を壊さずに対応を追加する PR を歓迎します。
   - SSO で多要素認証が必要な場合は、`--headed` で表示したウィンドウで手で完了できます（5 分以内）。自動の再ログインでは多要素認証に答えられないため、セッションが切れるたびに `manaba login --headed` を実行し直す必要があります。
   - エラーメッセージには、ログインが止まったページ（クエリ文字列は除去）が表示されます。デバッグの手がかりにしてください。
3. **コース一覧の表示形式。** manaba-cli はマイページのコース一覧を「リスト」表示から読み取ります。サムネイル表示や時間割表示になっている場合は、ブラウザで一度リスト表示に切り替えてください。

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `Not logged in to manaba`（終了コード 2） | `manaba login` を実行してください。何度も失敗する場合は `manaba login --headed` で様子を確認します。 |
| `The IdP rejected the username or password` | `manaba login --set-credentials` で正しいユーザー名とパスワードを保存し直してください。 |
| `SSO did not return to manaba within 60s` | ログイン中に想定外の画面（同意、多要素認証、パスワード変更など）が出ています。`manaba login --headed` で手で完了してください。 |
| ログインできるのに次のコマンドでまた失敗する | `manaba status` を実行してください。`logged_in` がすぐ `no` に戻る場合、大学側がセッションをブラウザに紐づけている可能性があります。`manaba --debug status` の出力を添えて Issue を作成してください。 |
| `Could not find … (selector)`（終了コード 3） | manaba の HTML がパーサの想定と異なります。ページは `~/.cache/manaba-cli/last-error.html` に保存されています。匿名化した一部分を添えて Issue を作成してください（[CONTRIBUTING](CONTRIBUTING.md#reporting-a-selector-break) を参照）。 |
| `Course list table not found` | ブラウザでマイページのコース一覧を **リスト** 表示に切り替えてください。 |
| `The system keyring is not usable` | Linux の場合、GNOME Keyring または KWallet をインストールし、ロックを解除してください。 |
| macOS でキーチェーンへのアクセス確認が何度も出る | **常に許可** を選んでください。ツールを再インストールすると、もう一度だけ確認が出ることがあります。 |
| `Browser login failed: … Chromium distribution 'chrome' is not found` | Google Chrome をインストールしてください。 |

## セキュリティ

- **パスワード：** システムのキーリングにだけ保存します。ディスクへの書き込み、画面表示、ログ出力は一切しません。
- **Cookie：** `~/.config/manaba-cli/cookies.json` には manaba と IdP のセッション Cookie が入っています（パーミッション 0600）。このファイルを読める人は、セッションが切れるまであなたとして manaba を操作できます。共有したりコミットしたりしないでください。
- **通信先：** 通信するのは、設定した manaba サイトと大学のログインページだけです。テレメトリや解析、その他のサーバーへの送信はありません。`base_url` 以外の URL は拒否します。
- **ログ：** `--debug` が出力するのは、クエリ文字列を除いた URL とステータスコードだけです。Cookie、SAML のデータ、フォームの値は出力しません。
- **解析エラー時の保存ファイル：** `last-error.html` には自分のコースのページがそのまま入っています。共有する前に匿名化してください。

脆弱性の報告方法は [SECURITY.md](SECURITY.md) を参照してください。

## アンインストール

```sh
uv tool uninstall manaba-cli
rm -rf ~/.config/manaba-cli ~/.cache/manaba-cli
security delete-generic-password -s manaba-cli     # macOS：保存したパスワードを削除
```

## 開発への参加

不具合の報告、修正、対応大学の追加を歓迎します。まず [CONTRIBUTING.md](CONTRIBUTING.md)（英語）をお読みください。読み取り専用のルールは変更できません。

セレクタの参考：[book000/get-manaba](https://github.com/book000/get-manaba)（MIT）。すべてのセレクタは、実際の manaba で英語と日本語の両方の画面について確認し直しています。

## ライセンス

[MIT](LICENSE)
