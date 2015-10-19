var app = {
    //d3 static scales.
    force: d3.layout.force(),

    //Current zoom.
    scale: 1,
    translate: [0, 0],
    dist_extent: [0,0],

    //Binary states.
    node: false,
    names: false,
    tokenViz: true,

    //Context menu.
    context: false,
    selection: false,

    //Graph data.
    matrix: undefined,
    documents: [],
    topics: [],
    distance: [],
    tokens: [],
    tokeni: {},

    //Bottombar data
    pins: []
};

function updateGraph() {
    "use strict";
    var type = d3.select("main select").property("value"),
        nodes,
        enter,
        data,
        range,
        color;

    if (type === "dist") {
        color = ["yellow", "blue"];
    } else if (type === "trend") {
        color = ["red", "green"];
    }

    //Create color distribution.
    range = app.topics.map(function (d) {
        if (d.zero) {
            return 0;
        }

        if (type == "dist" && app.context) {
            return app.matrix[app.context.id][d.id];
        }

        return d[type];
    });

    range.sort(d3.ascending);

    color = d3.scale.linear()
        .domain([
            d3.quantile(range,0.05),
            d3.quantile(range, 0.95)
        ])
//        .domain(app.dist_extent)
        .range(color);

    // Create and sort data.
    data = app.topics.slice(0)
        .sort(function (a, b) {
            return b.mean - a.mean;
        });

    nodes = d3.select("#graph g")
        .selectAll("g.node")
        .data(data, function (d) {
            return d.id;
        });

    enter = nodes.enter()
        .append("g")
        .attr("class", "node")
        .on("click", eventContext);

    enter.append("circle")
        .attr("class", "point");

    enter.append("text")
        .attr("class", "text");

    nodes.exit().remove();

    nodes.selectAll(".point")
        .attr("r", function (node) {
            return node.mean * 700;
        })
        .style("fill", function (node) {
            if (node.zero) {
                return "white";
            }
            if (type == "dist" && app.context) {
                return color(app.matrix[app.context.id][node.id]);
            }
            return color(node[type]);
        })
        .style("stroke", function (node) {
            return node.color;
        })
        .classed("high", function (d) {
            return d === app.context;
        })
        .classed("pin", function (d) {
            return app.pins.indexOf(d) > -1;
        });

    nodes.selectAll("text.text")
        .text(function (d) {
            return d.title;
        })
        .attr("x", function (d) {
            return d.x;
        })
        .attr("y", function (d) {
            return d.y;
        })
        .text(function (d) {
            if (app.names) {
                return d.title;
            }
            return '';
        });
}

function updateHelp() {
    "use strict";
    var type = d3.select(this).attr("alt"),
        info,
        display,
        header;

    if (type === "main") {
        info = "<p>The galaxy viewer visualizes is a geometric interpretation of each of the topics in the model. Each bubble represents a single topic. The size of each bubble corresponds to the token frequency of that topic. The greater proportion of tokens assigned to a topic, the larger the topic is represented. The white bubble in the center represents mathematical zero; in the case of topics zero is the theoretical topic where all words are represented in equal proportion.</p><p>The colour scheme of each topic is changeable using a dropbox in the top left hand corner. Currently two schemes are available.</p><p>Distance is a simple scheme that represents the relative distance from one topic to another. Yellow represents topics that are close together. Blue represents topics that are far apart. When no bubbles are selected the colours represent each topics distance from zero. Selected a bubble causes that topic to become the center of the representation.</p><p>Note: Topics at the center of the galaxy are naturally closer to outer bubbles than outer bubbles are to each other. This is a natural consequence of geometry.</p><p>In the trend colouring option each bubble is coloured based on a simple linear regression over time. If the frequency of tokens in that topic increase over time the bubble is coloured green. If the frequency decreases the topic is coloured red.</p><p>Note: The linear regression used to generate these colours does not check for normality. It is extremely likely that abnormalities in the data could skew results. As well, in order to maximize contrast, colours are generated relative to each other. If a majority of topics are decreasing, a topic that stays relatively still will display as green.</p>";

        header = "Galaxy Viewer";

    } else if (type === "documents") {
        info = "<p>The Documents panel displays the topic breakdown of each document in the corpus. Each pinned topic is represented by a specific colored line. Longer lines represent a greater prevalence of that topic in that document.</p><p>By default, The documents are sorted by prevalence over all topics. The document that has greatest representation of all pinned topics is placed at the top. However, if a pinned topic is selected, the documents are sorted by prevalence in that specific topic.</p>";

        header = "Documents";

    } else if (type === "tokens") {
        info = "<p>The Topic Tokens panel is a visualization of the specific words Mallet assigned to each topic. The chart shows absolute counts of each of the keywords assigned to each topic. Keywords can be removed using the checkboxes in the selection panel. Words that are not labeled as keys for this topic are not shown.</p><p>Note, this visualization does not show all keywords in a corpus. Instead, it shows keywords assigned to specific topics. Therefore, a keyword can appear separately in multiple topics.</p>";

        header = "Topic Tokens";

    } else if (type === "corpus_documents") {
        info = "<p>(Corpus) Document Counts is a static visualization of the number of documents in a corpus. It is not effected by pins and selections.</p>";

        header = "(Corpus) Document Counts";

    } else if (type === "corpus_tokens") {
        info = "<p>(Corpus) Token Counts is a static visualization of the number of tokens in a corpus. It is not effected by pins and selections.</p><p>Due to the aggressive pruning used in this prototype these counts represent only the tokens loaded by this visualization and not tokens in the entire corpus.</p>";

        header = "(Corpus) Token Counts";

    } else {
        info = "Unknown help screen.";
        header = "Unknown";
    }

    if (header !== d3.select("#help header h1").text()) {
        display = "visible";
        d3.select("#help header h1").text(header);
    } else {
        display = "hidden";
        d3.select("#help header h1").text('');
    }

    d3.select("#help")
        .style("visibility", display)
        .select("section")
        .html(info);
}

function updateSelection() {
    "use strict";
    var context,
        enter,
        data;

    if (app.pins.indexOf(app.selection) > -1) {
        data = app.selection;
    } else {
        data = {title: "", data: []};
    }

    //Change static nodes.
    context = d3.select('#pins section.bottom');

    context.select("h1")
        .text(data.title);

    //Edit fluid nodes
    context = context.select("ol")
        .selectAll("li")
        .data(data.data);

    enter = context.enter()
        .append("li");

    enter.append("input")
        .attr("type", "checkbox");

    enter.append("span")
        .attr("class", "label");

    context.exit().remove();

    context.select("input")
        .style("visibility", function (d) {
            return d.pruned
                ? "hidden"
                : "visible";
        })
        .property("checked", function (d) {
            return d.selected;
        })
        .on("change", function (d) {
            d.selected = d3.select(this).property("checked");
            updatePlugins();
            updateContext();
        });

    context.select("span")
        .text(function (d) {
            var word = app.tokens[d.word];
            if (word) {
                return word;
            }
            return d.word;
        });
}

function updateContext() {
    "use strict";
    var context,
        x = app.translate[0] + (app.context.x * app.scale),
        y = app.translate[1] + (app.context.y * app.scale),
        enter,
        top;

    //Change static nodes.
    context = d3.select('#context')
        .style('visibility', 'visible');

    context.select("h1")
        .text(app.context.title);

    context.select(".edit")
        .text("Edit Title")
        .on("click", editContext);

    //Edit fluid nodes
    context = context.select("ol")
        .selectAll("li")
        .data(app.context.data);

    enter = context.enter()
        .append("li");

    enter.append("span");
    enter.append("div")
        .attr("class", "tokenbar")
        .append("div")
        .attr("class", "tokendata");

    context.exit().remove();

    context.select("span")
        .text(function (d) {
            var word = app.tokens[d.word];
            if (word) {
                return word;
            }
            return d.word;
        });

    // Blue bars
    app.context.data.some(function (e) {
        if (e.selected) {
            top = e.count;
            return true;
        }
    });

    context.select("div.tokendata")
        .style("width", function (d) {
            if (d.selected) {
                return ((d.count / top) * 100) + "%";
            }
            return 0;
        });
}

function updateSize() {
    "use strict";
    var w = window.innerWidth,
        h = window.innerHeight;

    app.force.size([w, h]);

    d3.select("#graph")
        .style("width", w + "px")
        .style("height", h + "px");

    if (d3.select("#bottombar").attr("class").indexOf("expanded") > -1) {
        eventExpand(true);
    }
}

function updatePins() {
    "use strict";
    var topics,
        enter;

    topics = d3.select("#pins section.top ol")
        .selectAll("li")
        .data(app.pins);

    enter = topics.enter()
        .append("li");

    enter.append("span")
        .attr("class", "legend");

    enter.append("span")
        .attr("class", "label link");

    enter.append("button")
        .text("-");

    topics.exit().remove();
    topics.select("span.label")
        .text(function (x) {
            return x.title;
        });

    topics.select("li button")
        .on("click", function (node) {
            var index = app.pins.indexOf(node);
            app.pins.splice(index, 1);

            updatePins();
            updatePlugins();
            updateSelection();
            updateGraph();
        });

    topics.select("li span.legend")
        .style("background-color", function (d) {
            return d.color;
        });

    topics.selectAll("li span")
        .on("click", function (node) {
            app.selection = node;
            updateSelection();
            updatePlugins();
            updateGraph();
        });
}

function editContext() {
    "use strict";
    var context = d3.select("#context"),
        input = context.select("input"),
        link = context.select(".edit"),
        value;

    if (input.style("visibility") === "hidden") {
        input.style("visibility", "visible");
        link.text("save");
        input[0][0].focus();
    } else {
        //Change node title.
        value = input.property("value").trim();

        if (value !== "") {
            app.context.title = value;
        }

        context.select("h1")
            .text(app.context.title);

        //Edit html
        link.text("Edit Title");
        input
            .style("visibility", "hidden")
            .property("value", "");

        updateGraph();
        updatePins();
        updateSelection();
    }
}

function eventExpand(expand) {
    "use strict";
    var height = window.innerHeight / 2,
        node = d3.select("#bottombar"),
        newClass = (node.attr("class") === "small")
            ? "expanded"
            : "small",
        oldSize = parseInt(node.style("height"), 10),
        newSize = (newClass === "expanded")
            ? height
            : 35,
        i,
        orient;

    if (expand) {
        newClass = "expanded";
        newSize = height;
    }

    i = d3.interpolateRound(oldSize, newSize);

    d3.select("#bottombar")
        .attr("class", newClass)
        .transition()
        .styleTween("height", function () {
            return function (t) {
                var value = i(t) + "px";
                node.style("height", value);
                updatePlugins();
            };
        });

    orient = (newClass === "expanded")
        ? "rotate(180deg)"
        : "rotate(0deg)";


    d3.select(".expand")
        .style("transform", "translateY(-50%) " + orient);
}

function eventContext(node) {
    "use strict";
    //A hack to overwrite stupid complex interaction.
    if (!app.node) {
        eventRemoveContext();
    }

    if (d3.select(this).attr("id") === "graph") {
        app.node = false;
        return;
    }
    app.node = true;
    //endhack

    app.context = node;
    updateGraph();
    updateContext();
    updateSelection();
    updateGraph();
}

function eventRemoveContext() {
    "use strict";
    d3.select("#context")
        .style("visibility", "hidden")
        .select("input")
        .style("visibility", "hidden")
        .property("value", "");

    d3.select("#help")
        .style("visibility", "hidden");

    d3.select("#help header h1").text('');

    app.context = false;
    updateGraph();
}

function eventLoad() {
    "use strict";
    var data = d3.select("select.data").property("value");

    window.onresize = function () {
        updateSize();
        updatePlugins();
    };
    window.onresize();

    d3.select("main select")
        .on("change", updateGraph);

    d3.select("select.data")
        .on("change", function () {
            var href = location.href.split("?")[0] + "?data=" + d3.select(this).property("value");
            location.replace(href);
        });

    d3.select("body")
        .append("img")
        .attr("src", "static/ajax-loader.gif")
        .attr("class", "ajax");

    d3.select("#bottombar .shake")
        .on("click", function () {
            app.force.start();
        });

    d3.select("#bottombar .expand")
        .on("click", eventExpand);

    d3.select("#bottombar .names")
        .on("click", function () {
            app.names = !app.names;
            updateGraph();
        });

    d3.select("#context .pin")
        .on("click", function () {
            if (app.pins.indexOf(app.context) === -1) {
                app.pins.push(app.context);
            }

            app.selection = app.context;
            updatePins();
            updatePlugins();
            updateSelection();
            updateGraph();
            eventExpand(true);
        });

    d3.select("#context input")
        .on("keyup", function () {
            if (d3.event.keyCode === 13) {
                editContext();
            }
        });

    d3.selectAll(".help")
        .on("click", updateHelp);

    d3.selectAll("#bottombar select")
        .on("change", updatePlugins);

    d3.select("#graph")
        .on("click", eventRemoveContext)
        .call(
            d3.behavior.zoom()
                .on("zoom", function () {
                    var transform = "translate(" + d3.event.translate + ")" + " scale(" + d3.event.scale + ")";

                    app.scale = d3.event.scale;
                    app.translate = d3.event.translate;

                    eventRemoveContext();
                    d3.select("#graph g").attr("transform", transform);
                })
        )
        .on("click", eventContext);

    app.force
        .nodes(app.topics)
        .links(app.distance)
        .linkDistance(function (link) {
            return link.weight;
        })
        .friction(0)
        .charge(-0.01)
        .gravity(1)
        .on("tick", function () {
            d3.selectAll("#graph circle.point")
                .attr("cx", function (d) {
                    return d.x;
                })
                .attr("cy", function (d) {
                    return d.y;
                });

            d3.selectAll("#graph text.text")
                .attr("x", function (d) {
                    return d.x - 10;
                })
                .attr("y", function (d) {
                    return d.y - 10;
                });
        });

    function parse_int(value) {
        if (value.indexOf("e") > -1) {
            value = parseFloat(value);
        }
        return parseInt(value, 10);
    }

    function process_tokens(obj) {
        obj.id = parse_int(obj.id);

        app.tokens[obj.id] = obj.token;
        app.tokeni[obj.token] = obj.id;
    }

    // Depends on tokens.
    var category = d3.scale.category20();
    function process_topics(value) {
        //Static data
        value.id = parse_int(value.id);
        value.mean = parseFloat(value.mean);
        value.alpha = parseFloat(value.alpha);
        value.dist = parseFloat(value.dist);
        value.trend = parseFloat(value.trend);
        value.x = 500;
        value.y = 500;
        value.total = 0;
        value.title = value["key.0"];
        value.color = category(value.id);
        value.tokens = {};

        //Topic keys.
        value.data = [];
        Object.keys(value).forEach(function (key) {
            if (key.substring(0, 4) === "key.") {
                var index = app.tokeni[value[key]],
                    obj = {
                        selected: true,
                        word: index,
                        count: 0,
                        pruned: false
                    };

                if (index === undefined) {
                    obj.word = value[key];
                    obj.pruned = true;
                    obj.selected = false;
                }

                value.data[parse_int(key.substring(4))] = obj;
                delete value[key];
            }
        });

        app.topics[value.id] = value;
    }

    function process_documents (value) {
        //Static data.
        value.id = parse_int(value.id);

        //Metadata value for Token visualization.
        if (value.date === undefined) {
            value.date = null;
            app.tokenViz = false;
        }

        //Metadata value for Documents visualization.
        if (value.name === undefined) {
            value.name = value.source;
        }
        delete value.source;

        //Document topics.
        value.data = [];
        Object.keys(value).forEach(function (key) {
            if (key.indexOf("topic") > -1) {
                value.data[parse_int(key.substring(6))] = parseFloat(value[key]);
                delete value[key];
            }
        });
        app.documents[value.id] = value;
    }

    function process_state(state) {
        state.token = parse_int(state.token);
        state.doc = parse_int(state.doc);
        state.topic = parse_int(state.topic);
        state.count = parse_int(state.count);

        var topic = app.topics[state.topic],
            year = app.documents[state.doc].date,
            index = -1;

        topic.data.some(function (d, i) {
            if (d.word === state.token) {
                index = i;
                return true;
            }
        });

        //Increment total.
        topic.total += state.count;
        if (index > -1) {

            // Insert into token.
            if (topic.tokens[year] === undefined) {
                topic.tokens[year] = {};
            }

            if (topic.tokens[year][state.token] === undefined) {
                topic.tokens[year][state.token] = 0;
            }
            topic.tokens[year][state.token] += state.count;

            //Increment local.
            topic.data[index].count += state.count;
        }
    }

    function process_distance(dist) {
        var copy = [];
        Object.keys(dist).forEach(function (key) {
            copy[key] = parseFloat(dist[key]);
        });
        return copy;
    }

    d3.csv("data/" + data + "/tokens.csv", process_tokens, function () {
        d3.csv("data/" + data + "/topics.csv", process_topics, function () {
            d3.csv("data/" + data + "/documents.csv", process_documents, function () {
                d3.csv("data/" + data + "/state.csv", process_state, function () {
                    d3.csv("data/" + data + "/distance.csv", process_distance, function (distance) {

                        // Insert zero.
                        app.topics.push({
                            id: -1,
                            mean: 0.005,
                            x: 500,
                            y: 500,
                            zero: true,
                            title: "zero",
                            color: "white",
                            data: []
                        });

                        app.topics.forEach(function (source, i) {
                            app.topics.slice(i + 1).forEach(function (target) {
                                var weight;

                                if (source.zero) {
                                    weight = target.dist;
                                } else if (target.zero) {
                                    weight = source.dist;
                                } else {
                                    weight = distance[source.id][target.id];
                                }

                                app.distance.push({
                                    "source": source,
                                    "target": target,
                                    "weight": weight
                                });
                            });
                        });

                        var merged = [];
                        app.dist_extent = d3.extent(merged.concat.apply(merged, distance))

                        app.matrix = distance;

                        //Update visualization.
                        updateGraph();
                        app.force.start();
                        d3.select(".ajax").remove();
                        delete app.tokeni;
                    });
                });
            });
        });
    });
}
