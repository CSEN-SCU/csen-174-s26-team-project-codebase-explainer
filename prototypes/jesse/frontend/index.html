<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>GitMap</title>

<style>
body {
    background:#1e1e2f;
    color:white;
    font-family:Arial;
    padding:40px;
}
textarea {
    width:100%;
    height:150px;
    padding:10px;
}
button {
    margin-top:10px;
    padding:10px;
}
.card {
    margin-top:20px;
    background:#2f3640;
    padding:15px;
    border-radius:10px;
}
</style>
</head>

<body>

<h1>🚀 GitMap Analyzer</h1>
<p>This tool helps developers understand code by analyzing structure and generating AI explanations.ç</p>

<div class="card">
This tool analyzes code structure and uses AI to explain it.
</div>

<textarea id="input"></textarea>
<button onclick="run()">Analyze</button>

<div id="result"></div>

<script>
function run() {
    const text = document.getElementById("input").value;

    document.getElementById("result").innerHTML = "Analyzing...";

    fetch("http://localhost:8080", {
        method:"POST",
        body:text
    })
    .then(r=>r.json())
    .then(data=>{
        let html = `<div class="card"><b>Functions:</b><br>`;
        data.functions.forEach(f => html += f + "<br>");
        html += "</div>";

        html += `<div class="card"><b>AI:</b><br>${data.ai}</div>`;

        document.getElementById("result").innerHTML = html;
    })
    .catch(()=>{
        document.getElementById("result").innerHTML = "❌ Error";
    });
}
</script>

</body>
</html>
