# 開発メモ

## フロントエンドのモックを動かす方法
- frontend/main.ts の `Axios.defaults.baseURL = 'http://localhost:3000' // mockサーバーを設定`のコメントアウトを外す。
- frontendのディレクトリで`npm run json-mock`
- frontendのディレクトリで`npm run serve`

## ローカルでバックエンド・フロントエンドを動かす方法
- frontend/main.ts の `Axios.defaults.baseURL = 'http://localhost:3000' // mockサーバーを設定`をコメントアウトする。
- frontendのディレクトリで`npm run build`
- backend/view.pyの`LOCAL_ENV`を`True`にする。
- ルートで`python main.py`を実行

## デプロイする時
- backend/view.pyの`LOCAL_ENV`を`False`にする。