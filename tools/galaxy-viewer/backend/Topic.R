library("compiler", lib.loc="/usr/lib/R/library")

Topic <- function(v) {
  #New softmax
  exponent = exp(as.numeric(v))
  exponent = exponent / sum(exponent)
  class(exponent) <- "Topic"
  
  return (exponent)
}

Topic.add <- function (x, y) {
  top = x * y
  bottom = sum(top)
  return(top / bottom)
}

Topic.scale <- function (x, a) {
  top = x^a
  bottom = sum(top)
  return (top / bottom)
}

Topic.neg <- function (x) {
  return (Topic.scale(x, -1))
}

Topic.dot <- cmpfun(function (x, y) {
  powerx <- log(x)
  powery <- log(y)
  
  products <- mapply(function (xr, yr) {
    sum((powerx - xr) * (powery - yr))
  }, powerx, powery)
  
  sum(products)
})

Topic.length <- cmpfun(function (x) {
  powerx <- log(x)

  products <- sapply(powerx, function (xr) {
    sum((powerx - xr)^2)
  })
  sqrt(mean(products))
})

Topic.distance <- function (x, y) {
  difference = Topic.add(x, Topic.neg(y))
  return (Topic.length(difference))
}