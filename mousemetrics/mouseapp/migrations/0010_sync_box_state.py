from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mouseapp", "0009_box_pk_swap"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="box",
                    name="id",
                    field=models.BigAutoField(primary_key=True, serialize=False),
                ),
                migrations.AlterField(
                    model_name="box",
                    name="number",
                    field=models.IntegerField(),
                ),
                migrations.AddField(
                    model_name="box",
                    name="project",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="mouseapp.project",
                    ),
                ),
                migrations.AlterField(
                    model_name="box",
                    name="box_type",
                    field=models.CharField(
                        max_length=1,
                        choices=[("S", "Shoe"), ("T", "Stock")],
                        default="S",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="box",
                    constraint=models.UniqueConstraint(
                        fields=("project", "number"),
                        name="uniq_box_per_project",
                    ),
                ),
            ],
        ),
    ]
