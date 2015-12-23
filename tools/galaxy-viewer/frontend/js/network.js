var app = {
    // Database api
    //url: "http://sandbox.htrc.illinois.edu:6001",
    url: undefined,

    //d3 static scales.
    force: d3.layout.force(),

    //Current zoom.
    scale: 1,
    translate: [0, 0],

    //Binary states.
    node: false,
    names: false,

    //Context menu.
    context: false,
    selection: false,

    // Distance matrix.
    matrix: undefined,

    // Force data.
    topics: [],
    distance: [],

    //Bottombar data
    pins: [],

    documents: []
};

// Utilities
function get_distance(topic_x, topic_y, n) {
    "use strict";
    if (topic_x === topic_y) {
        return 0;
    }

    var x = Math.min(topic_x, topic_y),
        y = Math.max(topic_x, topic_y),
        i = parseInt((2 * x * n - Math.pow(x, 2) + 2 * y - 3 * x - 2) / 2);

    return app.matrix[i];
}

function keyValueLoop(obj, callback) {
    "use strict";
    Object.keys(obj).forEach(function (key) {
        callback(key, obj[key]);
    });
}

// Updates the main graph.
function updateGraph() {
    "use strict";
    var type = d3.select("main select").property("value"),
        nodes,
        enter,
        color;

    //Create color distribution.
    color = app.topics.map(function (d) {
        if (d.zero) {
            return 0;
        }

        if (type === "dist" && app.context) {
            return get_distance(app.context.id, d.id, app.topics.length);
        }

        return d[type];
    }).sort(d3.ascending);

    color = d3.scale.linear()
        .domain([
            d3.quantile(color, 0.05),
            d3.quantile(color, 0.95)
        ])
        .range(
            type === "dist"
                ? ["yellow", "blue"]
                : ["red", "green"]
        );

    // Create nodes
    nodes = d3.select("#graph g")
        .selectAll("g.node")
        .data(app.topics.slice(0)
            .sort(function (a, b) {
                return b.mean - a.mean;
            })
        );

    // Enter
    enter = nodes.enter()
        .append("g")
        .attr("class", "node")
        .on("click", eventGraphClick);

    enter.append("circle")
        .attr("class", "point");

    enter.append("text")
        .attr("class", "text");

    // Exit
    nodes.exit().remove();

    // Update
    nodes.select(".point")
        .attr("r", function (node) {
            return node.mean * 700;
        })
        .style("fill", function (node) {
            if (node.zero) {
                return "white";
            }
            if (type === "dist" && app.context) {
                return color(get_distance(app.context.id, node.id, app.topics.length));
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

    nodes.select("text.text")
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

// Update selection in bottom right of toolbar.
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
            return d.count
                ? "visible"
                : "hidden";
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
            return d.word;
        });
}

// Turns the topic context menu on.
function updateContext() {
    "use strict";
    function update() {
        var context,
            enter,
            maximum;

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
                return d.word;
            });

        // Blue bars
        maximum = app.context.data.reduce(function (prev, current) {
            if (current.selected && current.count > prev) {
                return current.count;
            }
            return prev;
        }, 0);

        context.select("div.tokendata")
            .style("width", function (d) {
                if (d.selected) {
                    return ((d.count / maximum) * 100) + "%";
                }
                return 0;
            });
    }

    // Only update if data is not already pulled.
    if (app.context.data === undefined) {
        var id = d3.select("main select.data").property("value"),
            url = app.url + "/datasets/" + id + "/topics/" + app.context.id + "/token_counts";

        d3.json(url, function (keywords) {
            app.context.data = keywords.token_counts.map(function (d) {
                return {
                    word: d[0],
                    count: d[1],
                    selected: true
                };
            });
            update();
        });
    } else {
        update();
    }
}

// Changes size of page.
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

// Updates the pins menu.
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

// Runs whenever edit is clicked.
function editContext() {
    "use strict";
    var context = d3.select("#context"),
        input = context.select("input"),
        link = context.select(".edit"),
        value;


    if (input.style("visibility") === "hidden") {
        // "Edit title" clicked. Reveal controls.
        input.style("visibility", "visible");
        link.text("save");
        input[0][0].focus();

    } else {
        // "Save" clicked. Save changes.
        value = input.property("value").trim();

        if (value !== "") {
            app.context.title = value;
        }

        context.select("h1")
            .text(app.context.title);

        //Edit html
        link.text("Edit Title");
        input.style("visibility", "hidden")
            .property("value", "");

        updateGraph();
        updatePins();
        updateSelection();
    }
}

// This event triggers whenever the bottom bar changes size.
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

// This function activates every time the graph is clicked.
function eventGraphClick(node) {
    "use strict";

    // if zero is clicked do nothing.
    if (node && node.id === -1) {
        return;
    }

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
    updateContext();
    updateGraph();
}

// This function removes the context box.
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

// This function runs every time a dataset changes.
function updateDataset() {
    "use strict";
    var id = d3.select("main select.data").property("value");

    // Reset data.
    d3.select("img.ajax")
        .style("visibility", "visible");

    app.selection = false;
    app.topics = [];
    app.distance = [];
    app.pins = [];
    eventRemoveContext();
    updatePins();
    updateSelection();
    updatePlugins();

    // Load new data.
    d3.json(app.url + "/datasets/" + id + "/topics/data?content=mean,center_dist,first_word,topic_dist,trend", function (topic_data) {

        // Collect data
        app.matrix = topic_data.topic_dist;
        var colors = d3.scale.category20(),
            count = topic_data.first_word.length;

        // Add topics
        d3.range(0, count - 1).forEach(function (d) {
            app.topics.push({
                id: d,
                mean: topic_data.mean[d],
                trend: topic_data.trend[d],
                dist: topic_data.center_dist[d],
                x: Math.random() * 1000,
                y: Math.random() * 1000,
                title: topic_data.first_word[d],
                color: colors(d)
            });
        });

        // Add zero.
        app.topics.push({
            id: -1,
            mean: 0.005,
            x: Math.random() * 1000,
            y: Math.random() * 1000,
            zero: true,
            title: "zero",
            color: "white"
        });

        // Insert edges
        app.topics.forEach(function (source, i) {
            app.topics.slice(i + 1).forEach(function (target) {
                var weight;

                if (source.zero) {
                    weight = target.dist;
                } else if (target.zero) {
                    weight = source.dist;
                } else {
                    weight = get_distance(source.id, target.id, count);
                }

                app.distance.push({
                    "source": source,
                    "target": target,
                    "weight": weight
                });
            });
        });

        // Update page
        updateGraph();
        updatePlugins();

        app.force
            .nodes(app.topics)
            .links(app.distance)
            .start();

        d3.select(".ajax").style("visibility", "hidden");
    });
}

// This function runs once on page load.
function eventLoad() {
    "use strict";
    window.onresize = function () {
        updateSize();
        updatePlugins();
    };
    window.onresize();

    // Top menu
    d3.select("main select.color")
        .on("change", updateGraph);

    d3.select("main select.data")
        .on("change", function () {
            updateDataset();
        });

    // Bottom bar buttons
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

    d3.selectAll("#bottombar select")
        .on("change", updatePlugins);

    // Context menu
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

    // Help menus
    d3.selectAll(".help")
        .on("click", updateHelp);

    // Normal click
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
        .on("click", eventGraphClick);

    // Set up force directed graph.
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

    // Upload dataset information.
    d3.json(app.url + "/datasets", function(json) {
        var data = window.location.search;
        if (data) {
            data = data.split("=")[1];
        }

        var options = d3.select("select.data")
            .selectAll("option")
            .data(json.datasets);

        options.enter().append("option");
        options.exit().remove();

        options.text(function (d) {
                return d.name;
            })
            .attr("value", function (d) {
                return d.id;
            })
            .property("selected", function (d) {
                if (d.name === data) {
                    return true;
                }
            });

        updateDataset();
    });
}
