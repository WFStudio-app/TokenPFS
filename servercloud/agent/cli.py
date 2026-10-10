"""Интерактивный режим агента: `python3 -m servercloud.agent`."""
import argparse
import getpass
import sys

from . import __version__
from .config import (DEFAULT_MODEL, NUM_CTX, OLLAMA_URL, delete_github_token,
                     load_github_token, save_github_token)
from .github import GitHubClient, GitHubError
from .llm import LLMError, OllamaClient
from .loop import Agent
from .permissions import Permissions
from .tools import ToolBox

HELP = """Команды:
  /help              эта справка
  /tools             список доступных инструментов
  /model [имя]       показать / сменить модель
  /ghtoken           ввести GitHub-токен (скрытый ввод, хранится в ~/.servercloud, chmod 600)
  /ghcheck           проверить токен
  /ghlogout          удалить токен
  /auto              вкл/выкл автоподтверждение правок файлов (bash и GitHub всё равно спрашивают)
  /reset             очистить историю диалога
  /exit              выход
Всё остальное — задача для агента."""


def build_agent(args):
    perms = Permissions(auto_edit=args.auto_edit, yolo=args.yolo)
    client = OllamaClient(args.url, args.model, num_ctx=NUM_CTX)
    token = load_github_token()
    tb = ToolBox(args.dir, perms, github=GitHubClient(token) if token else None,
                 allow_bash=not args.no_bash, allow_web=not args.no_web)
    agent = Agent(client, tb, max_steps=args.max_steps)
    return agent, client, tb, perms


def handle_command(line, agent, client, tb, perms):
    """Возвращает True, если нужно выйти."""
    cmd, _, rest = line.partition(" ")
    rest = rest.strip()
    if cmd in ("/exit", "/quit"):
        return True
    if cmd == "/help":
        print(HELP)
    elif cmd == "/tools":
        print(tb.describe())
    elif cmd == "/model":
        if rest:
            client.model = rest
            agent.native = True
            agent.refresh_system()
        print(f"модель: {client.model}")
        names = client.list_models()
        if names:
            print("установлены: " + ", ".join(names))
    elif cmd == "/ghtoken":
        token = rest or getpass.getpass("GitHub token (ввод скрыт): ").strip()
        if token:
            save_github_token(token)
            tb.set_github_token(token)
            agent.refresh_system()
            print("токен сохранён, GitHub-инструменты включены. Проверка: /ghcheck")
    elif cmd == "/ghcheck":
        tok = load_github_token()
        if not tok:
            print("токен не задан (/ghtoken)")
        else:
            try:
                u = GitHubClient(tok).request("GET", "/user")
                print(f"ok: {u.get('login')}")
            except GitHubError as e:
                print(f"ошибка: {e}")
    elif cmd == "/ghlogout":
        delete_github_token()
        tb.set_github_token(None)
        agent.refresh_system()
        print("токен удалён (если он был в переменной окружения — удалите её отдельно)")
    elif cmd == "/auto":
        perms.auto_edit = not perms.auto_edit
        print(f"автоподтверждение правок: {'ВКЛ' if perms.auto_edit else 'выкл'}")
    elif cmd == "/reset":
        agent.reset()
        print("история очищена")
    else:
        print("неизвестная команда, см. /help")
    return False


def run_repl(args):
    agent, client, tb, perms = build_agent(args)
    gh = "GitHub: вкл" if tb.github else "GitHub: выкл (/ghtoken)"
    print(f"ServerCloud Agent {__version__} | модель {client.model} | {tb.workdir} | {gh}")
    print("Введите задачу или /help.")
    while True:
        try:
            line = input("\nagent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line.startswith("/"):
            if handle_command(line, agent, client, tb, perms):
                return 0
            continue
        try:
            print("\n" + agent.run(line))
        except LLMError as e:
            print(f"✗ {e}")
        except KeyboardInterrupt:
            print("\n(прервано)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="servercloud-agent",
                                 description="Агент для кода на локальных моделях")
    ap.add_argument("task", nargs="*", help="задача (без неё — интерактивный режим)")
    ap.add_argument("-m", "--model", default=DEFAULT_MODEL)
    ap.add_argument("-d", "--dir", default=".", help="рабочая папка (песочница)")
    ap.add_argument("--url", default=OLLAMA_URL, help="адрес Ollama")
    ap.add_argument("--auto-edit", action="store_true", help="не спрашивать про правки файлов")
    ap.add_argument("--yolo", action="store_true",
                    help="не спрашивать про правки и bash (GitHub-запись всё равно спрашивает)")
    ap.add_argument("--no-bash", action="store_true")
    ap.add_argument("--no-web", action="store_true")
    ap.add_argument("--max-steps", type=int, default=15)
    args = ap.parse_args(argv)

    if args.task:
        agent, *_ = build_agent(args)
        try:
            print(agent.run(" ".join(args.task)))
        except LLMError as e:
            print(f"✗ {e}", file=sys.stderr)
            return 1
        return 0
    return run_repl(args)
