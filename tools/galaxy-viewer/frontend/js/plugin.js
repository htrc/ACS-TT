function updatePlugins() {
    d3.select("#viz1 div.inner").html("");
    d3.select("#viz2 div.inner").html("");
    d3.select("#viz1 h1").text("");
    d3.select("#viz2 h1").text("");
    ["viz1", "viz2"].forEach(function (area) {
        var type = d3.select("#" + area).select("select").property("value");

        d3.select("#" + area + " header img").attr("alt", type);

        if (type === "documents") {
            updateDocuments(area);
        } else if (type === "tokens") {
            updateTokens(area);
        } else if (type === "corpus_documents") {
            updateDocumentTotals(area);
        } else if (type === "corpus_tokens") {
            updateTokenTotals(area);
        }
    });
}

function setClass(area, string) {
    return d3.select("#" + area).select("div.inner")
        .attr("class", "inner " + string);
}

d3.selection.prototype.createSingle = function(select, node, attr) {
    if (!attr) {
        attr = {};
    }

    var viz = this.selectAll(select)
            .data([''])

    viz.enter()
        .append(node)
        .attr(attr);

    return viz;
}

function updateDocuments(area) {
    "use strict";
    var documents,
        viz,
        enter;

    //data
    documents = app.documents.map(function (doc) {
        var total;

        if (app.selection) {
            total = doc.data[app.selection.id];
        } else {
            total = app.pins.reduce(function (total, current) {
                if (doc.data[current.id] === undefined) {
                    return total;
                }
                return total + doc.data[current.id];
            }, 0)
        }



        return {
            id: doc.id,
            title: doc.name,
            values: app.pins.map(function (topic) {
                return {
                    value: doc.data[topic.id],
                    color: topic.color
                };
            }),
            total: total
        };
    });

    documents.sort(function (x, y) {
        return y.total - x.total;
    });
    documents = documents.slice(0, 30);

    //Visualization
    viz = setClass(area, "documentviz")
        .selectAll("section")
        .data(documents);

    enter = viz.enter()
        .append("section");

    enter.append("p");

    enter.append("div")
        .attr("class", "documentbar");

    viz.exit().remove();
    viz.select("p")
        .text(function (d) {return d.title; });

    viz
        .on("mouseover", function (d) {
            var mouse = d3.mouse(this),
                rect = this.getBoundingClientRect(),
                tooltip = d3.select("#tooltip")
                    .text('')
                    .style({
                        "display": "block",
                        "bottom": (window.innerHeight - rect.top) + "px",
                        "left": rect.left + "px"
                    });

            tooltip.append("h2").text(d.title);
            Object.keys(app.documents[d.id]).forEach(function (key) {
                if (key != "data" && key != "id" && key != "name") {
                    tooltip.append("p").text(key +": " + app.documents[d.id][key]);
                }
            });
        })
        .on("mouseout", function (node) {
            d3.select("#tooltip").style("display", "none");
        });

    viz.select("div.documentbar")
        .each(function (data) {
            var node = d3.select(this),
                width = parseInt(node.style("width"), 10);


            node = node.selectAll("div.documentdata")
                .data(data.values);

            node.enter()
                .append("div")
                .attr("class", "documentdata");

            node.exit().remove();

            node
                .style("width", function (d) {
                    return (d.value * width).toString() + "px";
                })
                .style("background-color", function (d) {
                    return d.color;
                });
        });
}

function dateFormat(date) {
    console.log(date)
    return date.getUTCFullYear() + "-" + (date.getUTCMonth() + 1) + "-" + date.getUTCDate();
}

function timeGraph(svg, data) {
    "use strict";
    var padding = [25, 25, 25, 65],
        nodes,
        lines = [],
        x,
        y,
        linegen;

    svg.attr("class", "timeGraph");

    d3.set(data.map(function (d) {return d.id; }))
        .values()
        .forEach(function (title) {
            title = parseInt(title, 10);
            var line = data.filter(function (d) {
                    return title === d.id;
                })
                .sort(function (x, y) {return x.date - y.date; });

            lines.push(line);
        });

    x = d3.time.scale.utc()
        .range([padding[3], parseInt(svg.style("width")) - padding[1]])
        .domain(d3.extent(data, function (d) {
            return d.date;
        }));

    y = d3.scale.linear()
        .range([padding[0], parseInt(svg.style("height")) - padding[2]])
        .domain([d3.max(data, function (d) {
            return d.count;
        }), 0]);

    linegen = d3.svg.line()
        .y(function (d) {return y(d.count); })
        .x(function (d) {return x(d.date); })
        .interpolate("linear");


    // Setup axis
    svg.createSingle("#xaxis", "g", {"id": "xaxis", "class": "xaxis axis"})
        .attr("transform", "translate(0," + (parseInt(svg.style("height")) - padding[2]) + ")")
        .call(
            d3.svg.axis()
                .scale(x)
                .orient("bottom")
                .ticks(5)
        );

    svg.createSingle("#yaxis", "g", {"id": "yaxis", "class": "yaxis axis"})
        .attr("transform", "translate(" + padding[3] + ", 0)")
        .call(
            d3.svg.axis()
                .scale(y)
                .orient("left")
        );

    //Data points
    nodes = svg.selectAll("circle")
        .data(data);

    nodes.enter()
        .append("circle")
        .attr("class", "point")
        .attr("r", 5);

    nodes.exit().remove();

    nodes
        .attr("fill", function (d) {return d.color; })
        .attr("cx", function (d) {return x(d.date); })
        .attr("cy", function (d) {return y(d.count); })
        .on("mouseover", function (d) {
            var rect = this.getBoundingClientRect(),
                tooltip = d3.select("#tooltip")
                    .text('')
                    .style({
                        "display": "block",
                        "bottom": (window.innerHeight - rect.top).toString() + "px",
                        "left": rect.right.toString() + "px"
                    });

            tooltip.append("h2").text(d.title);
            tooltip.append("p").text("date: " + dateFormat(d.date));
            tooltip.append("p").text("count: " + d.count);
        })
        .on("mouseout", function (node) {
            d3.select("#tooltip").style("display", "none");
        });

    //Paths
    nodes = svg.selectAll("path.path")
        .data(lines);

    nodes.enter()
        .append("path")
        .attr("class", "path")
        .style("stroke-width", 1)
        .style("fill", "none");

    nodes.exit().remove();

    nodes
        .attr("d", function (d) {return linegen(d); })
        .style("stroke", function (d) {return d[0].color; });
}

function updateTokens(area) {
    "use strict";
    // Setup container
    var svg = setClass(area, "tokenviz time")
        .createSingle("svg", "svg");

    if (!app.tokenViz) {
        svg.text("Tokens not available for this dataset.");
        return;
    }

    //Create data
    var data = [];
    app.pins.forEach(function (pin) {
        var words = pin.data.filter(function (d) {return d.selected; });

        Object.keys(pin.tokens).forEach(function (date) {
            // Align axis
            data.push({
                id: pin.id,
                date: new Date(date),
                color: pin.color,
                title: pin.title,
                count: words.reduce(function (total, word) {
                    if (pin.tokens[date][word.word]) {
                        return total + pin.tokens[date][word.word];
                    }
                    return total;
                }, 0)
            });
        });
    });

    // Create Graph
    timeGraph(svg, data);
}

function updateDocumentTotals(area) {
    svg = setClass(area, "doctotviz time")
        .createSingle("svg", "svg");

    var counts = {};
    app.documents.forEach(function (doc) {
        if (counts[doc.date] === undefined) {
            counts[doc.date] = 0;
        }
        counts[doc.date] += 1;
    });

    var data = [];
    Object.keys(counts).forEach(function (date) {
        data.push({
            date: new Date(date),
            color: "green",
            title: "totals",
            id: 0,
            count: counts[date]
        });
    });

    // Create Graph
    timeGraph(svg, data);
}

function updateTokenTotals(area) {
    svg = setClass(area, "toktotviz time")
        .createSingle("svg", "svg");

    var counts = {};
    app.topics.forEach(function (topic) {
        if (topic.tokens === undefined) {
            return;
        }

        Object.keys(topic.tokens).forEach(function (date) {
            var count = Object.keys(topic.tokens[date]).reduce(function (x, y) {
                return x + topic.tokens[date][y];
            }, 0);

            if (counts[date] === undefined) {
                counts[date] = 0;
            }
            counts[date] += count;
        });
    });

    var data = [];
    Object.keys(counts).forEach(function (date) {
        data.push({
            date: new Date(date),
            color: "green",
            id: 0,
            title: "totals",
            count: counts[date]
        });
    });

    // Create Graph
    timeGraph(svg, data);
}
