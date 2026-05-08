function showLoading(){

    document.getElementById("loading").style.display="block";
}

function toggleAnswer(card){

    const ans=card.querySelector(".answer");

    ans.style.display=
        ans.style.display==="block"
        ?"none"
        :"block";
}

/* =========================
   MINDMAP
========================= */

let network=null;
let nodesDataSet=null;
let edgesDataSet=null;
let allNodesData=[];

function buildGraph(text){

    if(!text || text.trim()==="") return;

    const lines=text
        .split('\n')
        .filter(l=>l.trim()!=="");

    let stack=[];
    let id=1;
    let edges=[];

    allNodesData=[];

    const baseIndent=
        lines[0].match(/^\s*/)[0].length;

    lines.forEach((line,index)=>{

        const rawIndent=
            line.match(/^\s*/)[0].length;

        const normalizedIndent=
            Math.max(0,rawIndent-baseIndent);

        const level=
            Math.floor(normalizedIndent/2);

        let labelText=line.trim()
            .replace(/^[•\-*#>\d.\s]+/,"")
            .replace(/\*\*/g,"")
            .trim();

        if(!labelText || labelText.length>40)
            return;

        const currentId=id++;

        while(stack.length>level){
            stack.pop();
        }

        const parentId=
            stack.length>0
            ?stack[stack.length-1].id
            :null;

        const nextLine=lines[index+1] || "";

        const nextIndent=
            Math.floor(
                Math.max(
                    0,
                    (nextLine.match(/^\s*/)?.[0].length||0)
                    -baseIndent
                )/2
            );

        const hasChildren=
            nextIndent>level;

        allNodesData.push({

            id:currentId,

            label:
                hasChildren
                ?`${labelText} ❯`
                :labelText,

            level:level,
            parentId:parentId,

            hidden:level>1,

            shape:"box",

            margin:{
                top:10,
                bottom:10,
                left:18,
                right:18
            },

            borderWidth:1.5,
            borderRadius:30,

            color:{
                background:
                    level===0
                    ?"#4338ca"
                    :"#1f2937",

                border:"#4b5563"
            },

            font:{
                color:"#f9fafb",
                size:level===0?15:13,
                face:"Inter"
            }
        });

        if(parentId!==null){

            edges.push({

                id:"e_"+parentId+"_"+currentId,

                from:parentId,
                to:currentId,

                hidden:level>1,

                width:1.5,

                color:{
                    color:"#4b5563",
                    opacity:.6
                },

                smooth:{
                    type:"cubicBezier",
                    forceDirection:"horizontal",
                    roundness:.8
                }
            });
        }

        stack.push({id:currentId});
    });

    nodesDataSet=new vis.DataSet(allNodesData);
    edgesDataSet=new vis.DataSet(edges);

    network=new vis.Network(

        document.getElementById("network"),

        {
            nodes:nodesDataSet,
            edges:edgesDataSet
        },

        {
            layout:{
                hierarchical:{
                    enabled:true,
                    direction:"LR",
                    nodeSpacing:70,
                    levelSeparation:260,
                    parentCentralization:true
                }
            },

            physics:false,

            interaction:{
                hover:true,
                zoomView:true,
                dragNodes:true
            }
        }
    );

    network.on("click",(params)=>{

        if(params.nodes.length>0){

            toggleChildren(params.nodes[0]);
        }
    });
}

function toggleChildren(nodeId){

    const children=
        allNodesData.filter(
            n=>n.parentId===nodeId
        );

    if(children.length>0){

        const isHidden=
            nodesDataSet.get(children[0].id).hidden;

        children.forEach(child=>{

            nodesDataSet.update({
                id:child.id,
                hidden:!isHidden
            });

            const edge=
                edgesDataSet.get()
                .find(e=>e.to===child.id);

            if(edge){

                edgesDataSet.update({
                    id:edge.id,
                    hidden:!isHidden
                });
            }
        });
    }
}

function expandAllNodes(){

    nodesDataSet.update(
        allNodesData.map(n=>({
            id:n.id,
            hidden:false
        }))
    );

    edgesDataSet.update(
        edgesDataSet.get().map(e=>({
            id:e.id,
            hidden:false
        }))
    );
}

function downloadMindMap() {

    if (!network) {

        alert("Mind map not loaded.");
        return;
    }

    expandAllNodes();

    // Save original size
    const container =
        document.getElementById("network");

    const originalWidth =
        container.style.width;

    const originalHeight =
        container.style.height;

    // 🚀 Temporary ultra-HD render size
    container.style.width = "4000px";
    container.style.height = "2500px";

    network.redraw();

    network.fit({
        animation: false
    });

    setTimeout(() => {

        const canvas =
            network.canvas.frame.canvas;

        const dataURL =
            canvas.toDataURL("image/png");

        // Download
        const link =
            document.createElement("a");

        link.href = dataURL;

        link.download =
            "brainboost-mindmap-HD.png";

        document.body.appendChild(link);

        link.click();

        document.body.removeChild(link);

        // Restore original size
        container.style.width =
            originalWidth;

        container.style.height =
            originalHeight;

        network.redraw();

        network.fit({
            animation: false
        });

    }, 1200);
}


/* =========================
   PAGE ROUTING
========================= */

window.onload=function(){

    const hasNotes = window.APP_DATA.hasNotes;
    
    const hasFlash = window.APP_DATA.hasFlash;
    
    const hasMap = window.APP_DATA.hasMap;

    document
        .getElementById("notes-view")
        .classList.add("hidden");

    document
        .getElementById("flash-view")
        .classList.add("hidden");

    document
        .getElementById("map-view")
        .classList.add("hidden");

    if(hasMap){

        document
            .getElementById("map-view")
            .classList.remove("hidden");

        const mapContent=
            document
            .getElementById("raw-map-data")
            .textContent
            .trim();

        if(mapContent!==""){

            buildGraph(mapContent);
        }

    }else if(hasFlash){

        document
            .getElementById("flash-view")
            .classList.remove("hidden");

    }else{

        document
            .getElementById("notes-view")
            .classList.remove("hidden");
    }

    document
        .getElementById("loading")
        .style.display="none";
};

const summaryBox = document.getElementById("summary-content");

if (summaryBox) {

    summaryBox.innerHTML = marked.parse(summaryBox.innerText);
}

