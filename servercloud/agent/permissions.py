"""Подтверждение опасных действий пользователем."""


class Permissions:
    """Виды действий: edit, write, bash — локально; github_write — запись на GitHub.

    --auto-edit разрешает edit/write без вопросов; --yolo разрешает ещё и bash.
    Запись на GitHub (github_write) НИКОГДА не одобряется автоматически,
    кроме явного ответа «a» в текущей сессии.
    """

    def __init__(self, auto_edit=False, yolo=False):
        self.auto_edit = auto_edit
        self.yolo = yolo
        self.always = set()

    def confirm(self, kind, title, detail=""):
        if kind != "github_write":
            if self.yolo:
                return True
            if self.auto_edit and kind in ("edit", "write"):
                return True
        if kind in self.always:
            return True
        print(f"\n\033[33m⚠ {title}\033[0m")
        if detail:
            print(detail)
        try:
            ans = input("  Разрешить? [y]да / [a]всегда в сессии / [N]нет: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        ans = ans.strip().lower()
        if ans in ("a", "all", "в"):
            self.always.add(kind)
            return True
        return ans in ("y", "yes", "д", "да")
