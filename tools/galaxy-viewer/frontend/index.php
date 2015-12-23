<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <link href="network.css" type="text/css" rel="stylesheet" />
        <script src="js/d3.v3.min.js" charset="UTF-8" ></script>
        <script src="js/plugin.js" charset="UTF-8" ></script>
        <script src="js/network.js" charset="UTF-8" ></script>
        <title>Topic Galaxy Visualization</title>
    </head>
    <body onLoad='eventLoad()'>
        <main>
            <header>
                <select class="color">
                    <option value='dist' selected>Distance</option>
                    <option value='trend'>Trend</option>
                </select>

                <select class="data">
                </select>

                <img src="static/white_help.png" class="button help header" alt="main">
            </header>
            <svg id="graph">
                <g />
            </svg>
        </main>

        <img src="static/ajax-loader.gif" class="ajax">

        <aside id="context">
            <header>
                <p class="link edit">Edit Title</p>
                <h1></h1>
                <input autocomplete="off">
                <img src="static/pin_topic.png" class="pin button">
            </header>

            <section>
                <ol>
                </ol>
            </section>
        </aside>

        <section id="bottombar" class="small">
            <header>
                <h1>Topic Modeling Galaxy Viewer</h1>
                <img src="static/up.png" class="button expand header" alt="Expand/Contract menu.">
                <img src="static/shake.png" class="button shake header" alt="Reset force directed graph.">
                <img src="static/name.png" class="button names header" alt="Toggles display names.">
            </header>
            <section>
                <section class="viz" id="viz1">
                    <header>
                        <select>
                            <option value="documents" selected>Documents</option>
                            <option value="tokens">Topic Tokens</option>
                            <option value="corpus_documents">(Corpus) Document Counts</option>
                            <option value="corpus_tokens">(Corpus) Token Counts</option>
                        </select>
                        <img src="static/question.png" class="button help header">
                    </header>
                    <div class="inner">
                    </div>
                </section>

                <section class="viz" id="viz2">
                    <header>
                        <select>
                            <option value="documents">Documents</option>
                            <option value="tokens" selected>Topic Tokens</option>
                            <option value="corpus_documents">(Corpus) Document Counts</option>
                            <option value="corpus_tokens">(Corpus) Token Counts</option>
                        </select>
                        <img src="static/question.png" class="button help header">
                    </header>
                    <div class="inner">
                    </div>
                </section>

                <section class="cell" id="pins">
                    <section class="top">
                        <header>
                            <h1>Selection</h1>
                        </header>
                        <ol>
                        </ol>
                    </section>
                    <section class="bottom">
                        <header>
                            <h1></h1>
                        </header>
                        <ol>
                        </ol>
                    </section>
                </section>

            </section>
        </section>

        <aside id="help">
            <header>
                <img src="static/question.png" class="button help header">
                <h1></h1>
            </header>
            <section>
                <p></p>
            </section>
        </aside>

        <aside id="tooltip">
        </aside>

        <script>
            <?php
            if (isset($_GET['d'])) {
                $url = $_GET['d'];
            } else {
                $url = "http://sandbox.htrc.illinois.edu:6001";
            }

            echo "app.url = '$url';";
            ?>
        </script>
    </body>
</html>
