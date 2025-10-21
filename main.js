import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";

const models = {
  view1: "mipoTest/F201.glb",
  view2: "mipoTest/E21P_BLOCK.glb",
  view3: "mipoTest/E22P_BLOCK.glb",
};

// 3D 뷰 인스턴스를 저장할 객체
const threeViews = {};

let isResizing = false;
let currentResizer = null;
let startX = 0;
let startY = 0;
let startWidth = 0;
let startHeight = 0;

// 리사이저 이벤트 초기화
function initResizers() {
  const resizers = document.querySelectorAll(
    ".resizer, .resizer-h-thin, .resizer-v-thin, .resizer-v-between"
  );

  resizers.forEach((resizer) => {
    resizer.addEventListener("mousedown", initResize);
  });

  // Right panel resizer
  const rightPanel = document.getElementById("rightPanel");
  rightPanel.addEventListener("mousedown", (e) => {
    const rect = rightPanel.getBoundingClientRect();
    if (e.clientX >= rect.left - 2 && e.clientX <= rect.left + 2) {
      e.preventDefault();
      isResizing = true;
      startX = e.clientX;
      startWidth = rightPanel.offsetWidth;
      currentResizer = { dataset: { resize: "right" } };
      rightPanel.classList.add("active");
      document.addEventListener("mousemove", resize);
      document.addEventListener("mouseup", stopResize);
    }
  });

  // Console resizer
  const consoleResizer = document.getElementById("consoleResizer");
  consoleResizer.addEventListener("mousedown", (e) => {
    e.preventDefault();
    isResizing = true;
    startY = e.clientY;
    const consoleEl = document.getElementById("console");
    startHeight = consoleEl.offsetHeight;
    currentResizer = { dataset: { resize: "console" } };
    consoleResizer.classList.add("active");
    document.addEventListener("mousemove", resize);
    document.addEventListener("mouseup", stopResize);
  });
}

// 콘솔 토글
window.toggleConsole = function () {
  const consoleEl = document.getElementById("console");
  const btn = consoleEl.querySelector(".toggle-btn");
  consoleEl.classList.toggle("collapsed");
  btn.textContent = consoleEl.classList.contains("collapsed") ? "▲" : "▼";

  // 콘솔 크기 변경 시 3D 뷰 업데이트
  setTimeout(() => updateAllViews(), 50);
};

// 왼쪽 패널 토글
window.toggleLeftPanel = function () {
  const leftPanel = document.getElementById("leftPanel");
  const btn = leftPanel.querySelector(".toggle-btn");
  leftPanel.classList.toggle("collapsed");
  btn.textContent = leftPanel.classList.contains("collapsed") ? "▶" : "◀";
  const form = document.getElementById("searchForm");
  form.style.display = leftPanel.classList.contains("collapsed") ? "none" : "block";
  
  const tree = document.getElementById("jstree");
  tree.style.display = leftPanel.classList.contains("collapsed") ? "none" : "block";

  // 패널 토글 시 3D 뷰 업데이트
  setTimeout(() => updateAllViews(), 50);
};

function initResize(e) {
  isResizing = true;
  currentResizer = e.target;
  startX = e.clientX;
  startY = e.clientY;

  currentResizer.classList.add("active");

    // iframe의 pointer-events 비활성화 (핵심!)
  const iframes = document.querySelectorAll('iframe');
  iframes.forEach(iframe => {
    iframe.style.pointerEvents = 'none';
  });

  const resizeType = currentResizer.dataset.resize;

  if (resizeType === "left") {
    startWidth = document.getElementById("leftPanel").offsetWidth;
  } else if (resizeType === "right") {
    startWidth = document.getElementById("rightPanel").offsetWidth;
  } else if (resizeType === "topRow") {
    const topRow = document.querySelector(".top-row");
    startHeight = topRow.offsetHeight;
  } else if (resizeType === "rightTop") {
    startHeight = document.getElementById("rightTop").offsetHeight;
  } else if (resizeType === "view1-h") {
    startWidth = document.getElementById("view1").offsetWidth;
  } else if (resizeType === "view1-v") {
    startHeight = document.querySelector(".top-row").offsetHeight;
  } else if (resizeType === "view3-h") {
    startWidth = document.getElementById("view3").offsetWidth;
  } else if (resizeType === "view3-v") {
    startHeight = document.querySelector(".bottom-row").offsetHeight;
  }

  document.addEventListener("mousemove", resize);
  document.addEventListener("mouseup", stopResize);

  e.preventDefault();
}

function resize(e) {
  if (!isResizing) return;

  const resizeType = currentResizer.dataset.resize;
  const dx = e.clientX - startX;
  const dy = e.clientY - startY;

  const setWidth = (el, width, min = 100, max = Infinity) => {
    if (width > min && width < max) {
      el.style.flex = "none";
      el.style.width = width + "px";
    }
  };

  const setHeight = (el, height, min = 100, max = Infinity) => {
    if (height > min && height < max) {
      el.style.flex = "none";
      el.style.height = height + "px";
    }
  };

  switch (resizeType) {
    case "left": {
      const newWidth = startWidth + dx;
      setWidth(document.getElementById("leftPanel"), newWidth);
      break;
    }

    case "right": {
      const newWidth = startWidth - dx;
      setWidth(document.getElementById("rightPanel"), newWidth, 150);
      break;
    }

    case "console": {
      const consoleEl = document.getElementById("console");
      const newHeight = startHeight - dy;
      setHeight(consoleEl, newHeight, 30, 500);
      break;
    }

    case "topRow": {
      const topRow = document.querySelector(".top-row");
      const newHeight = startHeight + dy;
      setHeight(topRow, newHeight);
      break;
    }

    case "rightTop": {
      const rightTop = document.getElementById("rightTop");
      const newHeight = startHeight + dy;
      setHeight(rightTop, newHeight);
      break;
    }

    case "view1-h": {
      const view1 = document.getElementById("view1");
      const view2 = document.getElementById("view2");
      const container = view1.parentElement;
      const totalWidth = container.clientWidth;
      const newWidth = startWidth + dx;
      const newView2Width = totalWidth - newWidth;

      if (newWidth > 150 && newView2Width > 150) {
        setWidth(view1, newWidth);
        setWidth(view2, newView2Width);
      }
      break;
    }

    case "view1-v": {
      const topRow = document.querySelector(".top-row");
      const newHeight = startHeight + dy;
      setHeight(topRow, newHeight);
      break;
    }

    case "view3-h": {
      const view3 = document.getElementById("view3");
      const rightTop = document.getElementById("rightTop");
      const totalWidth = view3.offsetWidth + rightTop.offsetWidth;
      const newWidth = startWidth + dx;

      if (newWidth > 150 && totalWidth - newWidth > 150) {
        setWidth(view3, newWidth);
        rightTop.style.flex = "1";
        void rightTop.offsetWidth;
      }
      break;
    }

    case "view3-v": {
      const bottomRow = document.querySelector(".bottom-row");
      const newHeight = startHeight + dy;
      setHeight(bottomRow, newHeight);
      break;
    }
  }

  // 리사이즈 중 3D 뷰 업데이트
  updateAllViews();
}

function stopResize() {
  if (isResizing) {
    isResizing = false;
    if (currentResizer && currentResizer.classList) {
      currentResizer.classList.remove("active");
    }
    document.getElementById("rightPanel").classList.remove("active");
    document.getElementById("consoleResizer").classList.remove("active");
    currentResizer = null;

      // iframe의 pointer-events 복구 (핵심!)
  const iframes = document.querySelectorAll('iframe');
  iframes.forEach(iframe => {
    iframe.style.pointerEvents = 'auto';
  });
  
    document.removeEventListener("mousemove", resize);
    document.removeEventListener("mouseup", stopResize);

    // 리사이즈 완료 후 최종 업데이트
    updateAllViews();
  }
}

// 모든 3D 뷰 업데이트
function updateAllViews() {
  Object.keys(threeViews).forEach((viewId) => {
    updateView(viewId);
  });
}

// 특정 3D 뷰 업데이트
function updateView(viewId) {
  const view = threeViews[viewId];
  if (!view) return;

  const container = document.getElementById(viewId);
  const width = container.clientWidth;
  const height = container.clientHeight;
  if (viewId === "view1") {
    console.log(`Updating view ${viewId}: ${width}x${height}`);
  }
  view.camera.aspect = width / height;
  view.camera.updateProjectionMatrix();
  view.renderer.setSize(width, height);
}

function initThreeView(viewId, modelPath) {
  const container = document.getElementById(viewId);
  container.innerHTML = "";

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf0f0f0);

  const camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / container.clientHeight,
    0.1,
    1000
  );
  camera.position.set(2, 2, 2);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  const light = new THREE.HemisphereLight(0xffffff, 0x444444);
  light.position.set(1, 1, 1);
  scene.add(light);

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
  directionalLight.position.set(2, 2, 2);
  scene.add(directionalLight);

  // 뷰 정보 저장
  threeViews[viewId] = { scene, camera, renderer, controls };

  const loader = new GLTFLoader();
  const dracoLoader = new DRACOLoader();
  dracoLoader.setDecoderPath(
    "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/libs/draco/"
  );
  loader.setDRACOLoader(dracoLoader);

  loader.load(
    modelPath,
    function (gltf) {
      const model = gltf.scene;
      const box = new THREE.Box3().setFromObject(model);
      const center = box.getCenter(new THREE.Vector3());

      scene.add(model);

      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z);
      const fitDistance = maxDim * 1.5;
      camera.position.set(
        center.x + fitDistance,
        center.y + fitDistance,
        center.z + fitDistance
      );
      camera.lookAt(center);
      controls.target.copy(center);

      animate();
    },
    undefined,
    function (error) {
      console.error(`Error loading ${modelPath}:`, error);
    }
  );

  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
}

// 콘솔 로그 함수
function logToConsole(message, type = "info") {
  const consoleContent = document.querySelector(".console-content");
  if (!consoleContent) return;

  const line = document.createElement("div");
  line.className = `console-line ${type}`;
  line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  consoleContent.appendChild(line);
  consoleContent.scrollTop = consoleContent.scrollHeight;
}
      const fileList = [
        { filename: "E21P_BLOCK.glb", imgSrc: "./images/E21P_BLOCK.PNG" },
        { filename: "E22P_BLOCK.glb", imgSrc: "./images/E22P_BLOCK.PNG" },
        { filename: "E23P_BLOCK.glb", imgSrc: "./images/E23P_BLOCK.PNG" },
        { filename: "E24P_BLOCK.glb", imgSrc: "./images/E24P_BLOCK.PNG" },
        { filename: "E31P_BLOCK.glb", imgSrc: "./images/E31P_BLOCK.PNG" },
        { filename: "E32C_BLOCK.glb", imgSrc: "./images/E32C_BLOCK.PNG" },
        { filename: "ME31P_CARL_001.glb", imgSrc: "./images/ME31P_CARL_001.PNG", },
        { filename: "ME31P_DMG_001_OPEM.glb", imgSrc: "./images/ME31P_DMG_001_OPEM.PNG", },
        { filename: "ME31P_GRT_001.glb", imgSrc: "./images/ME31P_GRT_001.PNG" },
        { filename: "ME31P_HRL_001.glb", imgSrc: "./images/ME31P_HRL_001.PNG" },
        { filename: "ME31P_HRL_002.glb", imgSrc: "./images/ME31P_HRL_002.PNG" },
        { filename: "ME31P_HRL_003.glb", imgSrc: "./images/ME31P_HRL_003.PNG" },
        { filename: "ME31P_HRL_004.glb", imgSrc: "./images/ME31P_HRL_004.PNG" },
        { filename: "ME31P_HRL_005.glb", imgSrc: "./images/ME31P_HRL_005.PNG" },
        { filename: "ME31P_HRL_006.glb", imgSrc: "./images/ME31P_HRL_006.PNG" },
        { filename: "ME31P_MST_001_R1.glb", imgSrc: "./images/ME31P_MST_001_R1.PNG", },
        { filename: "ME31PT_TH138.glb", imgSrc: "./images/ME31PT_TH138.PNG" },
        { filename: "ME31PT_TR169.glb", imgSrc: "./images/ME31PT_TR169.PNG" },
        { filename: "ME31PT_VA001.glb", imgSrc: "./images/ME31PT_VA001.PNG" },
        { filename: "ME31PT_VA007.glb", imgSrc: "./images/ME31PT_VA007.PNG" },
        { filename: "ME31PT_VA009.glb", imgSrc: "./images/ME31PT_VA009.PNG" },
        { filename: "ME31PT_VA020.glb", imgSrc: "./images/ME31PT_VA020.PNG" },
        { filename: "ME31PT_VN017.glb", imgSrc: "./images/ME31PT_VN017.PNG" },
        { filename: "ME31PT_VN063.glb", imgSrc: "./images/ME31PT_VN063.PNG" },
        { filename: "ME31PT_VN101.glb", imgSrc: "./images/ME31PT_VN101.PNG" },
        { filename: "ME31PT_VN103.glb", imgSrc: "./images/ME31PT_VN103.PNG" },
      ];
// GLB 테이블 표시 함수 (임시 구현)
      function displayGLBTable(containerId, columns = 4) {
        const container = document.getElementById(containerId);
        if (!container) {
          console.error(`Container with ID ${containerId} not found`);
          return;
        }

        // Set container width to 80% of parent
        container.style.width = "99%";
        container.style.margin = "0 auto"; // Center the container horizontally

        // Create scrollable wrapper div
        const scrollWrapper = document.createElement("div");
        scrollWrapper.style.maxHeight = "500px"; // Adjust height as needed
        scrollWrapper.style.overflowY = "auto";
        scrollWrapper.style.border = "1px solid #ccc";
        scrollWrapper.style.borderRadius = "4px";

        // Create table element
        const table = document.createElement("table");
        table.style.width = "100%";
        table.style.borderCollapse = "collapse";
        table.style.margin = "10px 0";

        // Calculate number of rows needed
        const rows = Math.ceil(fileList.length / columns);

        // Create table rows
        for (let i = 0; i < rows; i++) {
          const row = document.createElement("tr");

          // Create table cells for each row
          for (let j = 0; j < columns; j++) {
            const index = i * columns + j;
            const cell = document.createElement("td");
            cell.style.padding = "10px";
            cell.style.textAlign = "center";
            cell.style.border = "1px solid #ddd";

            if (index < fileList.length) {
              const item = fileList[index];

              // Create image element
              const img = document.createElement("img");
              img.src = item.imgSrc;
              img.alt = item.filename;
              img.style.maxWidth = "150px";
              img.style.cursor = "pointer";
              img.style.display = "block";
              img.style.margin = "0 auto";

              // Add click event listener
              img.addEventListener("click", () => {
                loadModel(item.filename);
              });

              // Add hover effect
              img.addEventListener("mouseover", () => {
                img.style.opacity = "0.8";
              });
              img.addEventListener("mouseout", () => {
                img.style.opacity = "1";
              });

              cell.appendChild(img);

              // Add filename caption
              const caption = document.createElement("div");
              caption.textContent = item.filename.replace(".glb", "");
              caption.style.marginTop = "5px";
              caption.style.fontSize = "12px";
              cell.appendChild(caption);
            }

            row.appendChild(cell);
          }

          table.appendChild(row);
        }

        // Clear container, append scroll wrapper, and add table to wrapper
        container.innerHTML = "";
        scrollWrapper.appendChild(table);
        container.appendChild(scrollWrapper);
      }

// 레이아웃 리셋 함수
window.resetLayout = function() {
  console.log("Layout reset");
  // 레이아웃 리셋 로직 구현
};

// 전체화면 토글 함수
window.toggleFullscreen = function() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    }
  }
};

// 레이아웃 저장 함수
window.saveLayout = function() {
  console.log("Layout saved");
  // 레이아웃 저장 로직 구현
};

// 검색 함수들
window.search승선 = function() {
  const value = document.getElementById("승선").value;
  logToConsole(`호선 검색: ${value}`, "info");
};

window.select설계부서 = function() {
  const value = document.getElementById("설계부서").value;
  logToConsole(`블럭 검색: ${value}`, "info");
};

window.search도면번호 = function() {
  const value = document.getElementById("도면번호").value;
  logToConsole(`도면번호 검색: ${value}`, "info");
};

async function selectBlock() {
  const block = document.getElementById("idBlock").value;
  logToConsole(`블럭 선택: ${block}`, "info");

  const res = await fetch('http://localhost:4000/api/auth/getBlockTree', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ block })
  });

  const data = await res.json();

  // 기존 트리 제거
  $('#jstree').jstree('destroy');

  // 새 트리 생성
  $('#jstree')
    .jstree({
      core: { data: data },
      plugins: ['checkbox', 'state']
    })
    .on('ready.jstree', function () {
      $(this).jstree('open_all');
    })
    .on('select_node.jstree', async function (e, selected) {
      const node = selected.node;
      logToConsole(`노드 선택: ${node.text}`, "warning");

      // 선택 시 다시 트리 로딩
      // const res = await fetch('http://localhost:4000/api/auth/getBlockTree', {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json'
      //   },
      //   body: JSON.stringify({ block: node.text }) // 또는 다른 기준
      // });

      // const newData = await res.json();
      // $('#jstree').jstree('destroy');
      // $('#jstree').jstree({
      //   core: { data: newData },
      //   plugins: ['checkbox', 'state']
      // }).on('ready.jstree', function () {
      //   $(this).jstree('open_all');
      // });
    });

  console.log(data);
}

// 초기화 함수
function init() {
  // 리사이저 초기화
  //selectBlock();

  // 윈도우 리사이즈 이벤트
  window.addEventListener("resize", () => {
    updateAllViews();
  });

  // 3D 뷰 초기화
  initThreeView("view1", models.view1);
  logToConsole("view1 초기화", "info");

  initThreeView("images", models.view2);
  logToConsole("view2 초기화", "info");

  initThreeView("view3", models.view3);
  logToConsole("view3 초기화", "info");

  displayGLBTable("view2", 4);
  logToConsole("Images 초기화 완료", "success");



  // jsTree 초기화 - treeData가 3dData.js에서 로드되었는지 확인
  $(function () {
    registerUser();
  //   if (typeof treeData !== "undefined") {
  //     $("#jstree")
  //       .jstree({
  //         core: {
  //           data: treeData,
  //         },
  //         plugins: ["state"],
  //         plugins: ['checkbox'],
  //       })
  //       .on("ready.jstree", function () {
  //         $(this).jstree("open_all");
  //       })
  //       .on("select_node.jstree", function (e, data) {
  //         const node = data.node;
  //         logToConsole(`노드 선택: ${node.text}`, "warning");
  //       });
  //   } else {
  //     console.error("treeData is not defined. Please check 3dData.js");
  //   }
  });
}

// DOMContentLoaded 이벤트에서 초기화
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
  registerUser();
} else {
  init();
}

window.selectBlock = selectBlock;