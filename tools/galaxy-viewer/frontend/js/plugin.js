// Utility functions
function setClass(area, string) {
    "use strict";
    return d3.select("#" + area).select("div.inner")
        .attr("class", "inner " + string);
}

d3.selection.prototype.createSingle = function (select, node, attr) {
    "use strict";
    if (!attr) {
        attr = {};
    }

    var viz = this.selectAll(select)
        .data(['']);

    viz.enter()
        .append(node)
        .attr(attr);

    return viz;
};

function dateFormat(date) {
    "use strict";
    // return date.getUTCFullYear() + "-" + (date.getUTCMonth() + 1) + "-" + date.getUTCDate();
    return date.getUTCFullYear();
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

    // Filter out invalid dates
    data = data.filter(function (d) {
        return !isNaN(d.date.getTime());
    });

    // Create line
    d3.set(data.map(function (d) { return d.id;}))
        .values()
        .forEach(function (title) {
            title = parseInt(title, 10);
            var line = data.filter(function (d) {
                    return title === d.id;
                })
                .sort(function (x, y) { return x.date - y.date; });

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
                        "bottom": (window.innerHeight - rect.top) + "px",
                        "left": rect.right + "px"
                    });

            tooltip.append("h2").text(d.title);
            tooltip.append("p").text("year: " + dateFormat(d.date));
            tooltip.append("p").text("count: " + d.count);
        })
        .on("mouseout", function () {
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
        .style("stroke", function (d) {
            if (d.length > 0) {
                return d[0].color;
            } else {
                return "white";
            }
        });
}

// Main update function.
function updatePlugins() {
    "use strict";
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

// Plugins
function complexGraph(get_value, name, callback) {
    "use strict";
    var data = {
        id: false,
        value: {},
    };

    function update(area) {

        // If dataset not selected yet don't do anything.
        var id = d3.select("main select.data").property("value");
        if (!id) {
            return;
        }

        // Reset database if dataset changes.
        if (data.id !== id) {
            data.value = {};
            data.id = id;
            data.index = {};
        }

        // Create our data.
        app.pins.forEach(function (pin) {
            if (data.value[pin.id] === undefined) {
                data.value[pin.id] = "in progress";
                d3.json(app.url + "/datasets/" + id + "/topics/" + pin.id + get_value, function (json) {
                    data.value[pin.id] = json;
                    data.value[pin.id].self = pin;
                    update(area);
                });
            }
        });

        // reset container
        d3.select("#" + area + " div.inner").html("");
        d3.select("#" + area + " h1").text("");

        var svg = setClass(area, name);

        callback(svg, data.value);
    }

    return update;
}

var updateDocuments = complexGraph("/doc_prominence", "documentviz", function (svg, data) {
    "use strict";
    var documents,
        viz,
        enter;

    if (!app.selection.id || !data[app.selection.id].doc_prominence) {
        return;
    }

    // create index
    if (data.index === undefined) {
        data.index = {};
    }

    if (data.index[app.selection.id] === undefined) {
        data.index[app.selection.id] = {}
        data[app.selection.id].doc_prominence
            .map(function (d) {
                return d;
            })
            .forEach(function (d) {
                data.index[app.selection.id][d.volid] = d
            });
    }

    documents = data[app.selection.id].doc_prominence
        .slice(0, 30)
        .map(function (doc) {
            return {
                id: doc.volid,
                date: new Date(doc.publishDate),
                title: doc.title,
                author: doc.author,
                values: app.pins.map(function (pin) {
                    return {
                        value: data.index[pin.id][doc.volid].prominence,
                        color: data[pin.id].self.color
                    };
                })
            };
        });

    //Visualization
    viz = svg.createSingle("div", "div")
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

    viz.on("mouseover", function (d) {
            var rect = this.getBoundingClientRect(),
                tooltip = d3.select("#tooltip")
                    .text('')
                    .style({
                        "display": "block",
                        "bottom": (window.innerHeight - rect.top) + "px",
                        "left": rect.left + "px"
                    });

            tooltip.append("h2").text(d.title);
            if (d.author) {
                tooltip.append("p").text("Author: " + d.author);
            }
            tooltip.append("p").text("Year: " + dateFormat(d.date));
        })
        .on("mouseout", function () {
            d3.select("#tooltip").style("display", "none");
        });

    viz.on("click", function (d) {
        if (isNaN(parseInt(d.id.charAt(0)))) {
            var url = "http://babel.hathitrust.org/cgi/pt?id=" + d.id;
            window.open(url, '_blank');
        }
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
                    return (d.value * width) + "px";
                })
                .style("background-color", function (d) {
                    return d.color;
                });
        });

});

var updateTokens = complexGraph("/token_counts_by_year", "tokenviz time", function (svg, data) {
    "use strict";
    //Create visualization data.
    svg = svg.createSingle("svg", "svg");

    var graphData = [];

    app.pins.forEach(function(pin) {

        // Skip in progress data.
        if (data[pin.id] === "in progress") {
            return;
        }

        // Create selection object.
        var selection = {};
        app.topics[pin.id].data.forEach(function (word) {
            selection[word.word] = word.selected;
        });

        // Loop over dates
        keyValueLoop(data[pin.id], function (date, words) {
            if (date === "self" || date === "null") {
                return;
            }

            graphData.push({
                id: parseInt(pin.id, 10),
                date: new Date(date),
                color: data[pin.id].self.color,
                title: data[pin.id].self.title,
                count: Object.keys(words).reduce(function (total, word) {
                    if (selection[word]) {
                        return total + words[word];
                    }
                    return total;
                }, 0)
            });
        });
    });

    timeGraph(svg, graphData);
});

function simpleGraph(get_value, name) {
    "use strict";
    var data = {
        id: false,
        value: false
    };

    return function (area) {

        // Abort because of race conditions.
        var id = d3.select("main select.data").property("value");
        if (!id || data.value === "in progress") {
            return;
        }

        // Prepare div
        d3.select("#" + area + " div.inner").html("");
        d3.select("#" + area + " h1").text("");

        var svg = setClass(area, name + " time")
            .createSingle("svg", "svg");

        // Get currently selected dataset.
        if (data.value === false || data.id !== id) {
            data.value = "in progress";
            data.id = id;

            d3.json(app.url + "/datasets/" + id + get_value, function (json) {
                data.value = Object.keys(json)
                    .filter(function (d) {
                        return d > 0;
                    })
                    .map(function (key) {
                        return {
                            date: new Date(key),
                            color: "green",
                            id: 0,
                            title: "totals",
                            count: json[key]
                        };
                    });
                timeGraph(svg, data.value);
            });
        } else {
            timeGraph(svg, data.value);
        }
    };
}

var updateTokenTotals = simpleGraph("/token_counts_by_year", "toktotviz"),
    updateDocumentTotals = simpleGraph("/doc_counts_by_year", "doctotviz");
