from django.db import connection, migrations


def drop_video_call_tables(apps, schema_editor):
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute("DROP TABLE IF EXISTS video_calls_callparticipant;")
            cursor.execute("DROP TABLE IF EXISTS video_calls_videocallroom;")
        else:
            cursor.execute("DROP TABLE IF EXISTS video_calls_callparticipant CASCADE;")
            cursor.execute("DROP TABLE IF EXISTS video_calls_videocallroom CASCADE;")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(drop_video_call_tables, noop_reverse),
    ]
