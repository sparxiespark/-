# File: map_widget.py
# 完善版功能：从数据库加载节点/边（使用 Length 作为权重）；交互式子图切换；点击起点/终点高亮最短路径（红粗线）；显示路径总长度；无路径提示。
# File: map_widget.py
import math
import heapq
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, 
                             QGraphicsTextItem, QGraphicsLineItem)
from PyQt5.QtGui import QPen, QBrush, QColor, QFont
from PyQt5.QtCore import Qt, QPointF

try:
    from db_utils import db_query_all
except ImportError:
    db_query_all = None

class MapWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # 基础设置
        self.setStyleSheet("background-color: #ffffff; border: none;")
        self.setRenderHint(0x01) # 抗锯齿
        self.setDragMode(QGraphicsView.ScrollHandDrag) # 支持拖拽
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.nodes = {}        # NodeID -> (x, y, ellipse_item)
        self.adj = {}          # NodeID -> {neighbor: length}
        self.path_lines = []   
        self.start_node = None
        self.end_node = None
        self.tip_text = None 

        self.load_and_draw_map()

    def load_and_draw_map(self):
        """完全从数据库加载点、边和权重"""
        if not db_query_all: return

        try:
            # 获取节点: NodeID, X, Y, Name
            nodes_rows = db_query_all("SELECT NodeID, X, Y, Name FROM Nodes")
            # 获取边: FromNode, ToNode, Length
            edges_rows = db_query_all("SELECT FromNode, ToNode, Length FROM Edges")

            if not nodes_rows: return

            nodes_dict = {row[0]: (row[1], row[2], row[3] or str(row[0])) for row in nodes_rows}
            
            # 构建邻接表
            self.adj = {nid: {} for nid in nodes_dict}
            for u, v, length in edges_rows:
                if u in nodes_dict and v in nodes_dict:
                    weight = float(length) if length is not None else 0.0
                    if weight <= 0: # 如果长度缺失则计算距离
                        x1, y1, _ = nodes_dict[u]
                        x2, y2, _ = nodes_dict[v]
                        weight = math.sqrt((x1-x2)**2 + (y1-y2)**2)
                    self.adj[u][v] = weight
                    self.adj[v][u] = weight

            self.draw_scene(nodes_dict)
        except Exception as e:
            print(f"Database Error: {e}")

    def draw_scene(self, nodes_dict):
        self.scene.clear()
        
        # 1. 重新创建提示文字 (解决 deleted 报错)
        self.tip_text = QGraphicsTextItem()
        self.tip_text.setZValue(100)
        self.scene.addItem(self.tip_text)
        self.update_tip("请点击起点")

        self.nodes.clear()
        self.path_lines.clear()
        self.start_node = None
        self.end_node = None

        # 2. 绘制原来的边 (更黑一点)
        edge_pen = QPen(QColor("#000000"), 2) # 纯黑
        drawn = set()
        for u, neighbors in self.adj.items():
            ux, uy, _ = nodes_dict[u]
            for v, _ in neighbors.items():
                if tuple(sorted((u, v))) in drawn: continue
                vx, vy, _ = nodes_dict[v]
                # Y轴向上修正：使用 -uy 和 -vy
                line = self.scene.addLine(ux, -uy, vx, -vy, edge_pen)
                line.setAcceptedMouseButtons(Qt.NoButton) # 不响应点击，防遮挡
                drawn.add(tuple(sorted((u, v))))

        # 3. 绘制节点
        for nid, (x, y, name) in nodes_dict.items():
            r = 10
            # Y轴向上修正：使用 -y
            ellipse = QGraphicsEllipseItem(x - r, -y - r, r*2, r*2)
            ellipse.setBrush(QBrush(Qt.black))
            ellipse.setPen(QPen(Qt.white, 1))
            ellipse.setData(0, nid)
            ellipse.setZValue(10)
            self.scene.addItem(ellipse)

            # 节点文字
            text = QGraphicsTextItem(name)
            text.setPos(x + 12, -y - 12)
            text.setAcceptedMouseButtons(Qt.NoButton) # 点击穿透
            self.scene.addItem(text)

            self.nodes[nid] = (x, y, ellipse)

        self.scene.setSceneRect(self.scene.itemsBoundingRect())
        # 初始时将提示文字放在场景左上角
        self.tip_text.setPos(self.scene.sceneRect().topLeft())

    def update_tip(self, msg):
        if self.tip_text:
            text = f"操作指南：点击起点 -> 点击终点显示路径\n当前状态: {msg}"
            self.tip_text.setPlainText(text)
            self.tip_text.setFont(QFont("微软雅黑", 10, QFont.Bold))

    def highlight_path(self, path, total_dist):
        # 清除旧路径
        for line in self.path_lines: self.scene.removeItem(line)
        self.path_lines.clear()

        if not path: return

        # 高亮红线
        path_pen = QPen(Qt.red, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            ux, uy, _ = self.nodes[u]
            vx, vy, _ = self.nodes[v]
            line = self.scene.addLine(ux, -uy, vx, -vy, path_pen)
            line.setZValue(5)
            self.path_lines.append(line)
        
        self.update_tip(f"到达终点！最短路径长度: {total_dist:.2f}")
 #dijkstra算法
    def dijkstra(self, start, end):    
        distances = {n: float('inf') for n in self.nodes}
        prev = {n: None for n in self.nodes}
        distances[start] = 0
        pq = [(0, start)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > distances[u]: continue
            if u == end: break
            for v, w in self.adj.get(u, {}).items():
                if d + w < distances[v]:
                    distances[v] = d + w
                    prev[v] = u
                    heapq.heappush(pq, (distances[v], v))
        path = []
        curr = end
        while curr is not None:
            path.append(curr)
            curr = prev[curr]
        return path[::-1], distances[end]

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        item = self.scene.itemAt(scene_pos, self.transform())

        if isinstance(item, QGraphicsEllipseItem):
            nid = item.data(0)
            if self.start_node is None:
                self.start_node = nid
                item.setBrush(QBrush(Qt.blue))
                self.update_tip(f"起点已选: {nid}，请选择终点")
            elif self.end_node is None and nid != self.start_node:
                self.end_node = nid
                item.setBrush(QBrush(Qt.green))
                path, dist = self.dijkstra(self.start_node, self.end_node)
                self.highlight_path(path, dist)
            else:
                # 重置逻辑
                for n in self.nodes.values(): n[2].setBrush(QBrush(Qt.black))
                self.start_node = nid
                self.end_node = None
                item.setBrush(QBrush(Qt.blue))
                self.highlight_path([], 0)
                self.update_tip(f"重置，新起点: {nid}")
            return
        super().mousePressEvent(event)