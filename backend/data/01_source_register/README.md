# Source Register

The master list of every source considered for MamaCare AI's knowledge base:
organization, URL, date checked, license/permission status, and a vetting
decision (approved / rejected + reason).

This is a real compliance and traceability artifact, not busywork. Nebo needs
to be able to answer "where did this medical claim come from and who vetted
it" for every piece of content the bot can say — especially since this starts
from zero (no sources collected yet). Nothing enters `data/02_raw` without a
row here first.

Prefer reputable, checkable sources: Wizara ya Afya (Tanzania MoH), WHO,
UNICEF, and established maternal-health NGOs operating in Tanzania. A single
spreadsheet or CSV in this folder is enough — don't over-engineer it into a
database before there's more than a handful of sources.

**Owner track:** Data & Knowledge
**Sprint:** 1 (first real task — sourcing and vetting starts Day 1 of
building, not as an afterthought)
