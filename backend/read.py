import models

for build in models.Build.select().order_by(models.Build.role, models.Build.player):
    print(build.player, build.god, build.role)
