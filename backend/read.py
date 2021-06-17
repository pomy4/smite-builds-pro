import models

for build in models.Build.select().order_by(models.Build.role, models.Build.player):
    print(build.player, build.god, build.role)

import pickle

with open('test2.p', 'rb') as f:
    builds = pickle.load(f)
    for build in builds:
        print(build)
