# ServerCloud Agent

Положите папку `servercloud/agent/` в корень репозитория ServerCloud (рядом с `core/`, `modules/`).

## Запуск
    ollama serve &
    ollama pull qwen2.5-coder:1.5b
    python3 -m servercloud.agent                    # интерактивно
    python3 -m servercloud.agent "найди баг в main.py"   # одна задача
    python3 -m servercloud.agent -d ~/myproj -m qwen2.5-coder:3b

## Подключение к REPL ServerCloud (servercloud_app.py)
В месте, где разбираются команды, добавьте:

    if cmd == "/agent":
        import argparse
        from servercloud.agent.cli import run_repl
        run_repl(argparse.Namespace(
            model="qwen2.5-coder:1.5b", dir=".", url=OLLAMA_URL,
            auto_edit=False, yolo=False, no_bash=False, no_web=False, max_steps=15))
        continue

## GitHub
1. github.com → Settings → Developer settings → Fine-grained tokens.
2. Выберите ТОЛЬКО нужные репозитории, срок жизни 30 дней,
   права: Contents, Issues, Pull requests = Read and write.
3. В агенте: /ghtoken (ввод скрыт) → /ghcheck.

## Безопасность
- Токен хранится в ~/.servercloud/github_token (chmod 600) или в GITHUB_TOKEN; в bash он не передаётся.
- Токен уходит только на api.github.com, редиректы запрещены, в выводе вырезается.
- Правки файлов, bash и ЛЮБАЯ запись на GitHub требуют подтверждения.
- fetch_url блокирует localhost и локальную сеть. Файлы только внутри рабочей папки.
- Текст из веба и issues помечен как недоверенный (защита от prompt injection).
