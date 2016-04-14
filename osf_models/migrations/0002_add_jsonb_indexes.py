# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-04-14 14:01
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('osf_models', '0001_initial'),
    ]
    tables = ['osf_models_node', ]
    fields = [
        'registered_meta',
        'wiki_pages_current',
        'wiki_pages_versions',
        'wiki_private_uuids',
        'file_guid_to_share_uuids',
        'child_node_subscriptions'
    ]
    base_create_sql = "CREATE INDEX indx_{}_ops ON {} USING GIN ({} jsonb_path_ops);"
    base_drop_sql = "DROP INDEX indx_{}_ops ON {};"

    operations = [
        # migrations.RunSQL(, reverse_sql="")
    ]

    for table in tables:
        for field in fields:
            operations.append(
                migrations.RunSQL(base_create_sql.format(field, table, field),
                                  reverse_sql=base_drop_sql.format(field, table))
            )
