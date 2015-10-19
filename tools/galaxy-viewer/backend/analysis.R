library("proxy")
source("Functions.R")

#input
setPath("mind")
#generate.topics("data", "import-dir")

print("Create data tables.")
data.topic <- create.topic.data()
data.doc   <- create.doc.data()

print("Create token data")
temp       <- create.state()
state      <- temp[[1]]
data.token <- temp[[2]]
state      <- trim.state(state, 2000)
data.token <- trim.token(data.token, state)

print("Insert topic strength metrics.")
data.topic$mean  <- create.means(data.doc)
data.topic$trend <- create.trend(state, data.doc)

print("Create topics")
topics <- create.topics(state)

print("Calculate distances.")
data.topic$dist <- create.dists(topics)

print("Write results.")
write.csv(data.doc, find.output("documents.csv"), row.names=FALSE)
write.csv(data.topic, find.output("topics.csv"), row.names=FALSE)
write.csv(data.token, find.output("tokens.csv"), row.names=FALSE)
write.csv(aggregate.state(state), find.output("state.csv"), row.names=FALSE)

print("Create distance matrix")
distance <- create.distance.matrix(topics)
write.csv(distance, find.output("distance.csv"))
