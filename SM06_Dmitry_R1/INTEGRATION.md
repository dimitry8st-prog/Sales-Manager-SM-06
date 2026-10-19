# Подключение и остаток полного SM-06

Компонент разрабатывается на точном read-only snapshot cp04 аудита 20261018. Хеши protected source — SHA256SUMS_PROTECTED.json. Наличие копии не подтверждает свежесть рабочего компьютера: receipt интегратора должен сверить эти хеши перед merge. При drift остановить затронутую интеграцию и согласовать обновлённую базу, не затирать рабочий SOURCE.

После возврата: независимая компонентная приёмка точного ZIP; отдельный integration owner проверяет именные резервы и копирует только принятый новый модуль/packs в согласованный каталог. Остальные исходники не менять. До установки backup + manifest, проверка restore, scoped rollback/reinstall. Наличие backup не равно успешному restore.

Не подключать save callback к реальному worker автоматически: actual save_materials может вести к AUTO/SEND_QUEUED/sales.send. Использовать offline recorder. NO_OUTBOUND сохраняется. Никаких provider/send/Make/workingDB действий по этому пакету.

Legacy sales_preparation_contract.py в audit source допускает EN/ES/DA/UK и отвергает ru-RU (D04). Этот внешний прежний seam не исправляется правкой пакета F130; устранение и доказательство согласования остаются у integration owner.

Остаток целого SM-06: актуальные trusted producers locale evidence и обработка mixed/unknown/classifier; campaign-scoped утверждённые реальные facts и языковые packs; сохранение pinned language/version между этапами, drift check; действительная цепочка писем/материалов/ответов/followup/handoff и QA; SM03 complete positive chain; эксплуатационная регрессия/мониторинг и отдельная активация. Нормализованный evidence dict — точка подключения, а не доказанный production trust boundary. Callback recorder не доказывает реальную БД, очередь или внешнюю отправку. UI source неизвестен; интерфейс не реализован и не входит в настоящий runtime seam.

Шаблоны authoring samples можно переводить и структурно тестировать без коммерческих фактов. Они не являются рабочей коммерческой базой или разрешением на отправку. Внешний QA должен проверить естественность украинского и остальных переводов, семантическую эквивалентность, отсутствие новых factual claims/цен/обещаний. Активировать языковые версии можно только через существующий owner-controlled release process после соответствующей приёмки.

Статусы различаются: CP0 PASS = пакет и прежние зависимости запускаются; CP1 PASS = компонентный harness; независимая semantic/component acceptance; offline installation; connected full SM06 acceptance. Ни один не подменяет следующий.
