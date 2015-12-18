source('Topic.R')
options(stringsAsFactors = FALSE)

path.input  <- "input"
path.output <- "output"
dir.create(path.input, showWarnings=FALSE)
dir.create(path.output, showWarnings=FALSE)

setPath <- function (path) {
  assign("path.input", paste(path.input, path, sep="/"), envir = .GlobalEnv)
  assign("path.output", paste(path.output, path, sep="/"), envir = .GlobalEnv)
  dir.create(path.input, showWarnings=FALSE)
  dir.create(path.output, showWarnings=FALSE)
}

generate.topics <- function (path.data, type="import-file", path.mallet="/home/ryan/Local/Mallet/bin/mallet") {
  #This script generates the topics.
  
  path.data        = paste(path.input, path.data, sep="/")
  file.mallet      = paste(path.input, "topic-input.mallet", sep="/")
  file.state       = paste(path.input, "topic-state.gz", sep="/")
  file.keys        = paste(path.input, "topic-keys.txt", sep="/")
  file.composition = paste(path.input, "topic-composition.csv", sep="/")
  
  #Import data
  run = paste(c(
    path.mallet, 
    type,
    "--input", path.data,
    "--output", file.mallet,
    '\\', 
    "--keep-sequence", 
    "--remove-stopwords"
  ), collapse=" ")
  system(run)
  
  #Train Topics
  run = paste(c(
    path.mallet, "train-topics",
    "--input", file.mallet,
    "\\",
    "--num-topics", 100,
    "--num-iterations", 1000,
    "--optimize-interval",  10,
    "--output-state", file.state,
    "--output-topic-keys", file.keys,
    "--output-doc-topics", file.composition
  ), collapse=" ")
  system(run)
  
  #unzip state
  run = paste(c(
    "gzip", "-d", "-f", file.state 
  ), collapse=" ")
  system(run)
}

find.input <- function (file) {
  return(paste(path.input, "/", file, sep=""))
}

find.output <- function (file) {
  return(paste(path.output, file, sep="/"))
}

create.topic.data <- function() {
  #Keys are the top words for each topic. 
  test <- scan(find.input("topic-keys.txt"), what="char", sep="\n")
  test <- strsplit(test, "\\s+")
  data.topic <- data.frame(do.call(rbind, test))
  
  num.keys = length(data.topic) - 3
  names(data.topic) = c("id", "alpha", paste("key", seq(0, num.keys), sep="."))
  
  data.topic$id <- as.numeric(data.topic$id)
  #Old school aplha
  data.topic$alpha <- as.numeric(gsub(",", ".", data.topic$alpha))
  
  data.topic$alpha <- as.numeric(data.topic$alpha)
  return(data.topic)
}

sort.doc.data <- function (theta) {
  #This is an old style compositions file. We need to reorganize.
  header   <- theta[,c("V1","V2")]
  theta$V1 <- NULL
  theta$V2 <- NULL
  
  value <- apply(theta, 1, function (row) {
    keys <- row[c(TRUE, FALSE)]
    values <- row[c(FALSE, TRUE)]
    return(values[order(keys)])
  })
  
  return(data.frame(header, t(value)))
}

create.doc.data <- function() {
  #Read compositions.
  theta <- read.table(find.input("topic-composition.csv"))
  
  #Test for old style data.
  if (all(theta[,3] == as.integer(theta[,3]))) {
    theta <- sort.doc.data(theta)
  }
  
  data.doc        <- data.frame(theta)
  names(data.doc) <- c("id", "source", paste("topic", seq(0,length(data.doc) - 3), sep="."))
  data.doc$source <- as.character(data.doc$source)
  
  #This needs to be generalized
  if (file.exists(find.input("metadata.csv"))) {
    metadata <- read.csv(find.input("metadata.csv"))
    data.doc <- merge(data.doc, metadata, by.x="source", by.y="source", sort=FALSE)
  }
  
  return(data.doc)
}

create.means <- function(data.doc) {
  data.doc <- data.doc[, grepl("topic", names(data.doc))]
  return(as.numeric(sapply(data.doc, mean)))
}

create.trend <- function(state, data.doc) {
  topics <- sort(unique(state$topic))
  
  # Date info is missing.
  if (!"date" %in% names(data.doc)) {
    return(rep(0, length(topics)))
  }
  
  #Create custom state object
  state.trend <- merge(state[,c("doc", "topic")], data.doc[,c("id", "date")], by.x="doc", by.y="id")
  state.trend$doc <- NULL
  
  value <- sapply(topics, function (topic) {
    state.small <- state.trend[state.trend$topic == topic,]
    trend.table <- table(state.small$date)
    
    dates <- names(trend.table)
    dates <- as.numeric(as.POSIXct(dates))
    values <- as.numeric(trend.table)
    
    slope <- lm(values ~ dates)$coefficients['dates']
    return(as.numeric(slope))
  })
  return(value)
}

create.state <- function() {
  # Try import.
  tryCatch({
    state <- TRUE
    state <- read.table(gzfile(find.input("topic-state")), comment.char='', quote='', skip=3)
    names(state) <- c("doc", "source", "pos", "typeindex", "type", "topic")
  }, 
  error = function (error) {
    print(error)
    
    # There are spaces in source. We need to do a slower import.
    state <- scan(gzfile(find.input("topic-state")), what="char", skip=3, sep="\n")
    state <- strsplit(state, " ")
    
    #Correct for spaces in filename.
    state <- lapply(state, function (row) {
      dif <- length(row) - 6
      value <- c(row[1], paste(row[2:(2+dif)], collapse=" "), tail(row, 4))
      return(value)
    })
    state <- as.data.frame(t(matrix(unlist(state), nrow=6)))
    names(state) <- c("doc", "source", "pos", "typeindex", "type", "topic")
    
    #Correct for data type.
    state$doc       <- as.numeric(state$doc)
    state$pos       <- as.numeric(state$pos)
    state$typeindex <- as.numeric(state$typeindex)
    state$topic     <- as.numeric(state$topic)
    
    state <<- state
    
  })
  
  print("import complete")
  #Create token data
  data.token <- state[,c("typeindex", "type")]
  data.token <- data.token[!duplicated(data.token),]
  names(data.token) <- c("id", "token")
  
  #Remove unneccessary state data
  state$source <- NULL
  state$type <- NULL
  #Deleting pos is lost information, but we don't need it.
  state$pos <- NULL
  names(state) <- c("doc", "token", "topic")
  
  return(list(state, data.token))
}

trim.state <- function (state, max=1000) {
  tokens <- table(state$token)
  tokens <- sort(tokens, decreasing=TRUE)
  tokens <- as.numeric(names(head(tokens, max)))
  
  data.state <- state[state$token %in% tokens,]
  return(data.state)
}

trim.token <- function (data.token, state) {
  keep <- unique(state$token)
  data.tokens.trim <- data.token[data.token$id %in% keep,]
  return(data.tokens.trim)
}

create.topics <- function (state.trim) {
  state.table <- state.trim[,c("token", "topic")]
  state.table <- table(state.table)
  topics <- apply(state.table, 2, Topic)
  return(topics)
}

aggregate.state <- function(data.state) {
  #Create state object
  data.state <- aggregate(list(count=rep(1, nrow(data.state))), data.state, length)
  return(data.state)
}

create.dists <- function(topics) {
  distance <- apply(topics, 2, Topic.length)
  return(distance)
}

create.distance.matrix <- function (topics) {
  dist = as.matrix(dist(t(topics), method=Topic.distance))
  return(dist)
}
