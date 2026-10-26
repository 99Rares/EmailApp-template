"""Emergency: remove every registered passkey, which switches password sign-in back on.

    ./reset_passkeys.sh          # on the server: lists them and asks for confirmation
    ./reset_passkeys.sh --yes    # no question

While a passkey is registered the password is refused. Use this if every device holding a passkey is lost.
It takes effect immediately, no restart needed. Then sign in with the password and add a new passkey.
"""
import sys
from contextlib import closing

from email_app import passkeys


def main():
    with closing(passkeys._db()) as conn:
        rows = conn.execute("SELECT label, created_at, last_used FROM passkeys ORDER BY created_at").fetchall()
        if not rows:
            print("No passkeys registered. Password sign-in is already on.")
            return
        print(f"{len(rows)} passkey(s):")
        for r in rows:
            print(f"  - {r['label']}  (added {r['created_at']}, last used {r['last_used'] or 'never'})")
        if "--yes" not in sys.argv and input("Remove ALL of them and switch password sign-in back on? Type yes: ").strip().lower() != "yes":
            raise SystemExit("Nothing changed.")
        removed = conn.execute("DELETE FROM passkeys").rowcount
        conn.commit()
    print(f"Removed {removed} passkey(s). Password sign-in is on again.")


main()
