#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MariaDB 트리 테이블에 데이터 삽입 스크립트
Path Enumeration 방식 사용
"""

import mysql.connector
from mysql.connector import Error

# MariaDB 연결 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'manager',
    'database': 'hull3d',
    'charset': 'utf8mb4'
}

def create_connection():
    """MariaDB 연결 생성"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            print(f"✅ MariaDB 연결 성공: {DB_CONFIG['database']}")
            return conn
    except Error as e:
        print(f"❌ 연결 오류: {e}")
        return None

def parse_path(full_path):
    """
    경로를 파싱하여 정보 추출
    
    Args:
        full_path: 전체 경로 (예: /AYF201/A110B/F210C/F201_DK3-1SP)
    
    Returns:
        dict: {
            'full_path': 전체 경로,
            'parent_path': 부모 경로,
            'node_name': 노드 이름,
            'node_level': 깊이
        }
    """
    if not full_path or full_path == '/':
        return None
    
    parts = [p for p in full_path.split('/') if p]
    
    if len(parts) == 0:
        return None
    
    node_level = len(parts)
    node_name = parts[-1]
    
    if len(parts) > 1:
        parent_path = '/' + '/'.join(parts[:-1])
    else:
        parent_path = None
    
    return {
        'full_path': full_path,
        'parent_path': parent_path,
        'node_name': node_name,
        'node_level': node_level
    }

def insert_tree_node(cursor, node_info):
    """단일 노드 삽입"""
    insert_query = """
        INSERT INTO tree_path_enum 
            (full_path, parent_path, node_name, node_level, is_leaf) 
        VALUES 
            (%(full_path)s, %(parent_path)s, %(node_name)s, %(node_level)s, TRUE)
        ON DUPLICATE KEY UPDATE 
            parent_path = VALUES(parent_path),
            node_name = VALUES(node_name),
            node_level = VALUES(node_level)
    """
    
    try:
        cursor.execute(insert_query, node_info)
        return True
    except Error as e:
        print(f"❌ 삽입 오류: {e}")
        return False

def update_parent_leaf_status(cursor, parent_path):
    """부모 노드의 is_leaf를 FALSE로 업데이트"""
    if not parent_path:
        return
    
    update_query = """
        UPDATE tree_path_enum 
        SET is_leaf = FALSE 
        WHERE full_path = %s
    """
    
    try:
        cursor.execute(update_query, (parent_path,))
    except Error as e:
        print(f"⚠️  부모 업데이트 경고: {e}")

def insert_tree_data_from_file(conn, file_path):
    """
    파일에서 트리 데이터를 읽어서 삽입
    
    Args:
        conn: DB 연결
        file_path: 입력 파일 경로
    """
    cursor = conn.cursor()
    
    inserted_count = 0
    skipped_count = 0
    error_count = 0
    
    # 중복 제거를 위한 set
    processed_paths = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                if not line or line in processed_paths:
                    skipped_count += 1
                    continue
                
                processed_paths.add(line)
                
                # 경로 파싱
                node_info = parse_path(line)
                
                if not node_info:
                    print(f"⚠️  라인 {line_num}: 잘못된 경로 형식 - {line}")
                    error_count += 1
                    continue
                
                # 부모 경로들도 먼저 삽입 (계층 구조 보장)
                current_parts = [p for p in line.split('/') if p]
                for i in range(1, len(current_parts) + 1):
                    partial_path = '/' + '/'.join(current_parts[:i])
                    partial_info = parse_path(partial_path)
                    
                    if partial_info:
                        if insert_tree_node(cursor, partial_info):
                            if i == len(current_parts):  # 실제 타겟 노드
                                inserted_count += 1
                            
                            # 부모 업데이트
                            if partial_info['parent_path']:
                                update_parent_leaf_status(cursor, partial_info['parent_path'])
                
                # 진행상황 표시
                if line_num % 100 == 0:
                    print(f"  처리 중... {line_num}개 라인")
                    conn.commit()
        
        # 최종 커밋
        conn.commit()
        
        print(f"\n{'='*60}")
        print(f"✅ 삽입 완료!")
        print(f"   - 삽입: {inserted_count}개")
        print(f"   - 건너뜀: {skipped_count}개")
        print(f"   - 오류: {error_count}개")
        print(f"{'='*60}\n")
        
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        conn.rollback()
    finally:
        cursor.close()

def insert_tree_data_from_list(conn, path_list):
    """
    리스트에서 트리 데이터 삽입
    
    Args:
        conn: DB 연결
        path_list: 경로 리스트
    """
    cursor = conn.cursor()
    
    inserted_count = 0
    all_paths = set()
    
    try:
        # 모든 경로와 그 부모 경로들 수집
        for path in path_list:
            path = path.strip()
            if not path:
                continue
            
            parts = [p for p in path.split('/') if p]
            
            # 현재 경로와 모든 부모 경로 추가
            for i in range(1, len(parts) + 1):
                partial_path = '/' + '/'.join(parts[:i])
                all_paths.add(partial_path)
        
        # 정렬 (부모가 먼저 삽입되도록)
        sorted_paths = sorted(all_paths, key=lambda x: (x.count('/'), x))
        
        print(f"총 {len(sorted_paths)}개 경로 삽입 시작...\n")
        
        for idx, path in enumerate(sorted_paths, 1):
            node_info = parse_path(path)
            
            if node_info:
                if insert_tree_node(cursor, node_info):
                    inserted_count += 1
                    
                # 부모 업데이트
                if node_info['parent_path']:
                    update_parent_leaf_status(cursor, node_info['parent_path'])
            
            if idx % 100 == 0:
                print(f"  처리 중... {idx}/{len(sorted_paths)}")
                conn.commit()
        
        conn.commit()
        
        print(f"\n{'='*60}")
        print(f"✅ 삽입 완료: {inserted_count}개")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        conn.rollback()
    finally:
        cursor.close()

def get_tree_statistics(conn):
    """트리 통계 조회"""
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 전체 노드 수
        cursor.execute("SELECT COUNT(*) as total FROM tree_path_enum")
        total = cursor.fetchone()['total']
        
        # 레벨별 노드 수
        cursor.execute("""
            SELECT node_level, COUNT(*) as count 
            FROM tree_path_enum 
            GROUP BY node_level 
            ORDER BY node_level
        """)
        level_stats = cursor.fetchall()
        
        # 리프 노드 수
        cursor.execute("SELECT COUNT(*) as leaf_count FROM tree_path_enum WHERE is_leaf = TRUE")
        leaf_count = cursor.fetchone()['leaf_count']
        
        print(f"\n{'='*60}")
        print(f"📊 트리 통계")
        print(f"{'='*60}")
        print(f"전체 노드: {total}개")
        print(f"리프 노드: {leaf_count}개")
        print(f"브랜치 노드: {total - leaf_count}개")
        print(f"\n레벨별 분포:")
        for stat in level_stats:
            print(f"  Level {stat['node_level']}: {stat['count']}개")
        print(f"{'='*60}\n")
        
    except Error as e:
        print(f"❌ 통계 조회 오류: {e}")
    finally:
        cursor.close()

# =====================================================
# 메인 실행
# =====================================================

if __name__ == '__main__':
    # 샘플 데이터
    sample_paths = [
        '/AYF201/A110B/F210C/F201_DK3-1SP',
        '/AYF201/A110B/F210C/F201_DK3-2SP',
        '/AYF201/A110B/F210C/F201_DK3-3SP',
        '/AYF201/A110B/F211P/F201_LB1P_01-1P',
        '/AYF201/A110B/F211P/F201_LB1P_01-2P',
    ]
    
    # DB 연결
    connection = create_connection()
    
    if connection and connection.is_connected():
        try:
            # 방법 1: 파일에서 읽기
            # insert_tree_data_from_file(connection, 'tree_paths.txt')
            
            # 방법 2: 리스트에서 삽입
            insert_tree_data_from_list(connection, sample_paths)
            
            # 통계 조회
            get_tree_statistics(connection)
            
        finally:
            connection.close()
            print("✅ DB 연결 종료")
    else:
        print("❌ DB 연결 실패")