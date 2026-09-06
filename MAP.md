# מפת lancecli

איך הספרייה בנויה — בלי לקרוא את הקוד. לקריאה של כמה דקות.

## הרעיון במשפט

`lancecli` הוא כלי שורת-פקודה לקריאה בלבד של דאטאסט Lance.
הוא לא טוען את הטבלה ל־pandas/DuckDB. הוא מדבר עם **pylance**, ודוחף כמה שיותר עבודה למנוע של Lance: בחירת עמודות, פילטר SQL, מיון, ומגבלה על מספר שורות.

## הצינור (כל בקשה עוברת כאן)

```
lancecli <פקודה> [דגלים]  URI
              │
              ▼
         cli.py          קורא דגלים, פותח דאטאסט, קורא ל־run_*
              │
              ▼
       dataset.py        lance.dataset(uri)  +  S3/גרסה/תג
              │
      ┌───────┴────────┐
      ▼                ▼
   scan.py        commands/*.py
   קריאת שורות     מטא-דאטה / סיכומים
   (show, take…)   (stat, schema…)
      │                │
      └───────┬────────┘
              ▼
        render.py        טבלת Rich / CSV / JSON / JSONL
              │
              ▼
           stdout
```

ארבע שכבות, בלי קפיצות. פקודה חדשה לא אמורה לפתוח דאטאסט לבד או להדפיס לבד אם כבר יש שכבה לזה.

## ארבעת קבצי הליבה

| קובץ | תפקיד |
|---|---|
| `src/lancecli/cli.py` | רק Typer: דגלים משותפים, `_open`, `_run`. בלי לוגיקת Lance. |
| `src/lancecli/dataset.py` | פתיחת URI (מקומי / S3), time-travel, `storage_options`. שגיאות משתמש → `LanceCliError`. |
| `src/lancecli/scan.py` | **כל** גישה לשורות: scanner, `take`, sample, parse של `--indices` ו־`--order-by`. |
| `src/lancecli/render.py` | איך זה נראה: טבלה, CSV, JSONL, קיטוע וקטורים, `stat` panel. |

`src/lancecli/commands/<שם>.py` — דק: מקבל דאטאסט **כבר פתוח**, קורא ל־scan/metadata, מדפיס דרך render.

## שתי דרכי קריאה

### 1. שורות (data path)

Lance scanner / `take`, לא "תביא הכל לפייתון".

| פקודה | מה קורה באמת |
|---|---|
| `show` | `ds.head` / `to_table` עם `columns`, `filter`, `order_by`, `limit` |
| `csv` / `jsonl` | `ds.to_batches` — זרם, בלי לטעון את כל הטבלה לזיכרון |
| `tail` | סופר שורות, ואז `offset` + `limit` בסוף |
| `take` | `ds.take(indexes)` — קפיצה למיקום שורה, **לא** סריקה מההתחלה |
| `sample` | מגריל אינדקסים (עם `--seed`) ואז `take` |
| `freq` | סורק **עמודה אחת** וסופר ערכים בפייתון (`Counter`) |

`--order-by` ב־`show`/`csv`/`jsonl`/`tail` נכנס ל־scanner.
ב־`take`/`sample` ממיינים את הטבלה הקטנה שכבר הגיעה.

### 2. מטא-דאטה (בלי לקרוא תוכן שורות)

| פקודה | מה זה |
|---|---|
| `stat` | מסך בריאות אחד: שורות, מחיקות, פרגמנטים, גודל, אינדקסים, רמזים |
| `inspect` | אותו מידע בפרוטרוט + סכמה מלאה |
| `schema` | שמות וטיפוסים (`--physical` = סכמת Lance הפנימית) |
| `count` | `count_rows` (עם `--filter` זה כבר scanner) |
| `versions` / `fragments` / `indices` | גרסאות, קבצים פיזיים, אינדקסים |

## `take` ו־`--order-by` (מה שמיוחד ל־Lance)

**אינדקס** = מיקום שורה חיה בגרסה שנפתחה (`0` ראשונה, `-1` אחרונה). זה לא עמודת `id`.
אחרי מחיקות, "שורה 5" היא החמישית שנשארה.

```
--indices 0,2:5,-1     שורות 0, 2, 3, 4, ואחרונה
--indices ::10         כל עשירית
```

**מיון** נכתב `age` או `age:desc,id`. בפקודות סריקה זה pushdown למנוע. אם יש scalar index על העמודה, `--filter` יכול להשתמש בו במקום סריקה מלאה.

## דגלים משותפים (כמעט לכל פקודה)

```
URI                     תיקייה מקומית או s3:// / gs:// / az://
-c / --columns          אילו עמודות (חובה בטבלאות רחבות)
--filter                תנאי SQL, נדחף ל־scanner
--order-by              מיון
-n / --head             כמה שורות (show/sample/tail ברירת מחדל 10; csv/jsonl = הכל)
--version / --tag / --asof   time travel — רק אחד
--format / --full
--endpoint-url, --storage-option, --aws-profile   אופציונלי — S3 עובד ממשתני סביבה
```

S3 בלי דגלים (מומלץ): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, ואם צריך endpoint מותאם `AWS_ENDPOINT_URL` + `AWS_DEFAULT_REGION`. דגלים ב־CLI דורסים env.

חריג: ב־`freq`, `-c` הוא **שם העמודה לספירה**, לא רשימת עמודות.

## שגיאות

| קוד יציאה | מתי |
|---|---|
| 0 | הצליח (גם `lancecli` בלי ארגומנטים = עזרה) |
| 1 | טעות משתמש: URI רע, `--indices` לא חוקי, פורמט לא נתמך |
| 2 | חריגה לא צפויה |

## איפה מה נמצא בדיסק

```
src/lancecli/
  cli.py, dataset.py, scan.py, render.py
  commands/     פקודה = קובץ
examples/events.lance    דמו (50 שורות) — README רץ עליו
tests/                   CliRunner + פיקסצ'ר של 110 שורות ואינדקס BTREE על age
```

## כלל ברזל

לא מוסיפים DuckDB/pandas לנתיב הנתונים.
פקודה חדשה = קובץ ב־`commands/` + רישום ב־`cli.py` + בדיקה + דוגמה ב־README.
גישת שורות חדשה = פונקציה ב־`scan.py`, לא בתוך הפקודה.
