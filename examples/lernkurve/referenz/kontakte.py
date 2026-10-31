import sys

from basis import JsonStore, cli, text


def gueltige_email(wert):
    wert = text(wert, "E-Mail")
    lokal, at, domain = wert.partition("@")
    vorne, punkt, hinten = domain.rpartition(".")
    if not at or not lokal or "@" in domain or not punkt or not vorne or not hinten:
        raise ValueError(f"Ungültige E-Mail: {wert}")
    return wert


class ContactBook(JsonStore):
    def _frei(self, email, ausser=None):
        for eintrag in self.items:
            if eintrag["id"] != ausser and eintrag["email"].lower() == email.lower():
                raise ValueError(f"E-Mail bereits vorhanden: {email}")

    def add(self, name, email):
        name = text(name, "Name")
        email = gueltige_email(email)
        self._frei(email)
        return self._new(name=name, email=email)

    def update_email(self, id, email):
        eintrag = self._find(id)
        email = gueltige_email(email)
        self._frei(email, ausser=id)
        eintrag["email"] = email
        self._save()


BEFEHLE = {
    "add": lambda s, n, e: s.add(n, e) and None,
    "list": lambda s: "\n".join(f"{e['id']} {e['name']} <{e['email']}>" for e in s.list()),
    "email": lambda s, i, e: s.update_email(int(i), e),
    "remove": lambda s, i: s.remove(int(i)),
}

if __name__ == "__main__":
    sys.exit(cli(ContactBook, BEFEHLE))
