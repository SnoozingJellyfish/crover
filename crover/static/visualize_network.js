//カーソルを合わせたときに表示する情報領域
var datatip = d3.select("#datatip");

var svg = d3.select("svg"),
    width = +svg.attr("width"),
    height = +svg.attr("height");

if (document.documentElement.clientWidth > 1000) {
    var scale = 1.5;
}
else {
    var scale = 1;
}
svg.attr('transform', `translate(0,0) scale(${scale})`);

var color = d3.scaleOrdinal(d3.schemeCategory10);

var simulation = d3.forceSimulation()
    //.velocityDecay(0.4)
    .force("link", d3.forceLink().id(function(d) { return d.id; }))
    .force("charge", d3.forceManyBody())
    .force("center", d3.forceCenter(width / 2, height / 2))
    //.force('colllision',d3.forceCollide(40))                                 //nodeの衝突半径：Nodeの最大値と同じ
    .force('positioningX',d3.forceX())                                        //詳細設定は後で
    .force('positioningY',d3.forceY());

//"svg"にZoomイベントを設定
var zoom = d3.zoom()
  .scaleExtent([1/4 ,4])
  .on('zoom', SVGzoomed);

svg.call(zoom);

//"svg"上に"g"をappendしてdragイベントを設定
var g = svg.append("g")
  .call(d3.drag()
  .on('drag', SVGdragged))

function SVGzoomed() {
  g.attr("transform", d3.event.transform);
}

function SVGdragged(d) {
  d3.select(this).attr('cx', d.x = d3.event.x).attr('cy', d.y = d3.event.y);
};

var link = g.append("g")
    .attr("class", "links")
    .selectAll("line")
    .data(graph.links)
    .enter().append("line")
      .attr("stroke","#999")  //輪郭線の色指定追加
      .attr("stroke-width", function(d) { return Math.sqrt(d.value) - 0.8; })
      .call(d3.drag()　              //無いとエラーになる。。
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended));

let wc_img = document.getElementById("wc_img");

var node = g.append('g')
    .attr('class', 'nodes')
    .selectAll('g')
    .data(graph.nodes)
    .enter()
    .append('g')
    .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

node.append('circle')
    .attr("r", function(d) { return Math.sqrt(d.count) / 20; })
    .attr('fill', function(d) { return color(d.group); })
    .on('mouseover', function(d){
          d3.select(this).attr('fill', 'red');
          datatip.style("left", d3.event.pageX + 20 + "px")
                  .style("top", d3.event.pageY + 20 + "px")
                  .style("z-index", 0)
                  .style("opacity", 1);
          datatip.select("h2")
                  .style("border-bottom", "2px solid " +color(d.group))
                  .style("margin-right", "0px")
                  .text(d.author);
          datatip.select("p")
                  .text(d.tweet);
          wc_img.src = word_cloud[d.group];
    })
    .on('mousemove', function(){
          datatip.style("left", d3.event.pageX + 20 + "px")
                  .style("top", d3.event.pageY + 20 + "px")
    })
    .on('mouseout', function(){
          d3.select(this).attr('fill', function(d) { return color(d.group); })  //カーソルが外れたら元の色に

          datatip.style("z-index", -1)
                 .style("opacity", 0)
    });
/*
node.append("title")
  .text(function(d) { return d.id; });


node.append("use")
    //.attr("xlink:href",function(d) {return "#circle"})
    .attr("r", function(d) { return Math.sqrt(d.count) / 20; })
    .attr('fill', function(d) { return color(d.group); })
    .on('mouseover', function(d){
          d3.select(this).attr('fill', 'red'); //カーソルが合ったら赤に

          datatip.style("left", d3.event.pageX + 20 + "px")
                  .style("top", d3.event.pageY + 20 + "px")
                  .style("z-index", 0)
                  .style("opacity", 1)
                  //.style('background-image', function() {if (typeof d.image === "undefined" ) {return  'url("image/unknown.png")' } else { return 'url("'+ d.image + '")'}})

          //datatip.select("h2")
                  //.style("border-bottom", "2px solid " +color(d.group))
                  //.style("margin-right", "0px")
                  //.text(d.id);

          datatip.select("p")
                  .text(d.tweet);
      })
    .on('mousemove', function(){
          datatip.style("left", d3.event.pageX + 20 + "px")
                  .style("top", d3.event.pageY + 20 + "px")
      })
    .on('mouseout', function(){
          d3.select(this).attr('fill', function(d) { return color(d.group); })  //カーソルが外れたら元の色に

          datatip.style("z-index", -1)
                 .style("opacity", 0)
      });
*/


simulation
  .nodes(graph.nodes)
  .on("tick", ticked);

simulation.force("link")
  .links(graph.links);

simulation.force('charge')
            .strength(function(d) {return -15})  //node間の力

simulation.force('positioningX')   //X方向の中心に向けた引力
    .strength(0.06)

simulation.force('positioningY')  //Y方向の中心に向けた引力
    .strength(0.06)

function ticked() {
link
    .attr("x1", function(d) { return d.source.x; })
    .attr("y1", function(d) { return d.source.y; })
    .attr("x2", function(d) { return d.target.x; })
    .attr("y2", function(d) { return d.target.y; });

node
    .attr("cx", function(d) { return d.x; })
    .attr("cy", function(d) { return d.y; })
    .attr('transform', function(d) {return 'translate(' + d.x + ',' + d.y + ')'}); //nodesの要素が連動して動くように設定
}

function nodeTypeID(d){
  return "circle"
}

function dragstarted(d) {
  if (!d3.event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}

function dragged(d) {
  d.fx = d3.event.x;
  d.fy = d3.event.y;
}

function dragended(d) {
  if (!d3.event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}

/*
Vue.component('retweet-word-cloud', {
    template: '#retweet-word-cloud',
    data:function(){
        return {
            retweet_word_cloud: word_cloud
            },
        }
    }
})

new Vue({
    el:'#app',
    //delimiters:['[[',']]']  //なぜかdelimiters変わらない
});
*/



