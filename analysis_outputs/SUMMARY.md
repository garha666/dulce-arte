# Project Analysis Summary

- Target repo: `C:\Users\skinm\OneDrive - INACAP\6 semestre\backend\ev3\dulce-arte`
- README present: `True`
- Task family: `unspecified`
- Top-level items: .env, .env.example, .git, .gitignore, AGENTS.md, GLOSSARY.md, MEMORY.md, README.md, api, db.sqlite3, deploy, docker-compose.yml, docs, drf, env, manage.py, prompts_ia.md, requirements.txt, seed_data.py, smoke_test.py
- Train entry candidates: env/Lib/site-packages/PIL/FitsImagePlugin.py, env/Lib/site-packages/django/contrib/postgres/constraints.py, env/Lib/site-packages/django/db/models/constraints.py, env/Lib/site-packages/pip/_vendor/rich/constrain.py
- Inference entry candidates: env/Lib/site-packages/asgiref/server.py, env/Lib/site-packages/django/contrib/staticfiles/management/commands/runserver.py, env/Lib/site-packages/django/core/management/commands/runserver.py, env/Lib/site-packages/django/core/management/commands/testserver.py, env/Lib/site-packages/django/core/servers/__init__.py
- Evaluation entry candidates: api/tests.py, env/Lib/site-packages/asgiref/testing.py, env/Lib/site-packages/django/conf/app_template/tests.py-tpl, env/Lib/site-packages/django/contrib/admin/tests.py, env/Lib/site-packages/django/contrib/auth/password_validation.py
- Task-relevant files: env/Lib/site-packages/django/contrib/admin/migrations/0002_logentry_remove_auto_add.py, env/Lib/site-packages/django/contrib/admin/migrations/0003_logentry_add_action_flag_choices.py, env/Lib/site-packages/django/contrib/admin/templatetags/log.py, env/Lib/site-packages/django/contrib/auth/migrations/0005_alter_user_last_login_null.py, env/Lib/site-packages/django/contrib/gis/geos/prototypes/topology.py

## Conservative Suggestions

- Read the main model or backbone file before changing configs.
- Verify the train entrypoint and config loading path before inserting new modules.
- Treat suspicious patterns as heuristics until confirmed by command-level evidence.

## Additional Documents

- `RESEARCH_MAP.md`
- `CHANGE_MAP.md`
- `EVAL_CONTRACT.md`
