from django.db import migrations

SQL = """
PRAGMA foreign_keys=OFF;
CREATE TABLE "new__mouseapp_box" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "box_type" varchar(1) NOT NULL,
    "project_id" integer NOT NULL REFERENCES "mouseapp_project"("id"),
    "number" integer NOT NULL,
    UNIQUE ("project_id","number")
);
INSERT INTO "new__mouseapp_box" ("box_type","project_id","number")
SELECT "box_type","project_id","number" FROM "mouseapp_box";
DROP TABLE "mouseapp_box";
ALTER TABLE "new__mouseapp_box" RENAME TO "mouseapp_box";
UPDATE "mouseapp_mouse" AS m
SET "box_id" = (
  SELECT b."id"
  FROM "mouseapp_box" AS b
  WHERE b."project_id" = m."project_id"
    AND b."number" = m."box_id"
)
WHERE EXISTS (
  SELECT 1
  FROM "mouseapp_box" AS b
  WHERE b."project_id" = m."project_id"
    AND b."number" = m."box_id"
);
PRAGMA foreign_keys=ON;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("mouseapp", "0005_auto_20251022_1548"),
    ]

    operations = [
        migrations.RunSQL(SQL),
    ]
