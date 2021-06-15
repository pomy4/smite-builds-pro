import pickle
import models

with open('test.p', 'rb') as f:
    builds = pickle.load(f)
for build in builds:
    models.Build.create(player=build['name'], role=build['role'], god=build['god'])
