#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MariaDB 트리 테이블에 CSV 데이터 삽입 스크립트 (Description 포함)
Path Enumeration 방식 사용
"""

import mysql.connector
from mysql.connector import Error
import csv

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
    if not full_path or full_path == '\\':
        return None
    
    parts = [p for p in full_path.split('\\') if p]
    
    if len(parts) == 0:
        return None
    
    node_level = len(parts)
    node_name = parts[-1]
    
    if len(parts) > 1:
        parent_path = '\\' + '\\'.join(parts[:-1])
    else:
        parent_path = None
    
    return {
        'full_path': full_path,
        'parent_path': parent_path,
        'node_name': node_name,
        'node_level': node_level
    }

def insert_tree_node(cursor, node_info, description=None):
    """
    단일 노드 삽입 (description 포함)
    
    Args:
        cursor: DB 커서
        node_info: 노드 정보 dict
        description: 노드 설명 (선택)
    """
    insert_query = """
        INSERT INTO tree_path_enum 
            (full_path, parent_path, node_name, node_level, is_leaf, description) 
        VALUES 
            (%(full_path)s, %(parent_path)s, %(node_name)s, %(node_level)s, TRUE, %(description)s)
        ON DUPLICATE KEY UPDATE 
            parent_path = VALUES(parent_path),
            node_name = VALUES(node_name),
            node_level = VALUES(node_level),
            description = COALESCE(VALUES(description), description)
    """
    
    try:
        params = {**node_info, 'description': description}
        cursor.execute(insert_query, params)
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

def insert_tree_data_from_csv(conn, csv_file_path):
    """
    CSV 파일에서 트리 데이터를 읽어서 삽입
    CSV 형식: full_path,description
    
    Args:
        conn: DB 연결
        csv_file_path: CSV 파일 경로
    """
    cursor = conn.cursor()
    
    inserted_count = 0
    skipped_count = 0
    error_count = 0
    
    # 중복 제거를 위한 dict (경로 -> description)
    path_descriptions = {}
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            
            for line_num, row in enumerate(csv_reader, 1):
                # 빈 줄 건너뛰기
                if not row or len(row) < 1:
                    skipped_count += 1
                    continue
                
                # CSV에서 경로와 설명 추출
                full_path = row[0].strip()
                description = row[1].strip() if len(row) > 1 else None
                
                if not full_path:
                    skipped_count += 1
                    continue
                
                # 경로와 설명 저장
                path_descriptions[full_path] = description
                
                # 진행상황 표시
                if line_num % 100 == 0:
                    print(f"  읽는 중... {line_num}개 라인")
        
        print(f"\n총 {len(path_descriptions)}개의 고유 경로 발견\n")
        
        # 모든 경로와 그 부모 경로들 수집
        all_paths = set()
        for path in path_descriptions.keys():
            parts = [p for p in path.split('\\') if p]
            
            # 현재 경로와 모든 부모 경로 추가
            for i in range(1, len(parts) + 1):
                partial_path = '\\' + '\\'.join(parts[:i])
                all_paths.add(partial_path)
        
        # 정렬 (부모가 먼저 삽입되도록)
        sorted_paths = sorted(all_paths, key=lambda x: (x.count('\\'), x))
        
        print(f"총 {len(sorted_paths)}개 경로 (부모 포함) 삽입 시작...\n")
        
        for idx, path in enumerate(sorted_paths, 1):
            node_info = parse_path(path)
            
            if not node_info:
                error_count += 1
                continue
            
            # 해당 경로의 description 가져오기 (있으면)
            desc = path_descriptions.get(path, None)
            
            if insert_tree_node(cursor, node_info, desc):
                inserted_count += 1
                
                # 부모 업데이트
                if node_info['parent_path']:
                    update_parent_leaf_status(cursor, node_info['parent_path'])
            
            if idx % 100 == 0:
                print(f"  처리 중... {idx}/{len(sorted_paths)}")
                conn.commit()
        
        # 최종 커밋
        conn.commit()
        
        print(f"\n{'='*60}")
        print(f"✅ 삽입 완료!")
        print(f"   - 삽입: {inserted_count}개")
        print(f"   - 건너뜀: {skipped_count}개")
        print(f"   - 오류: {error_count}개")
        print(f"   - Description 포함: {len([d for d in path_descriptions.values() if d])}개")
        print(f"{'='*60}\n")
        
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {csv_file_path}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cursor.close()

def insert_tree_data_from_list(conn, data_list):
    """
    리스트에서 트리 데이터 삽입 (경로, 설명 튜플)
    
    Args:
        conn: DB 연결
        data_list: [(path, description), ...] 형식의 리스트
    """
    cursor = conn.cursor()
    
    inserted_count = 0
    path_descriptions = {}
    all_paths = set()
    
    try:
        # 데이터 수집
        for path, desc in data_list:
            path = path.strip()
            if not path:
                continue
            
            path_descriptions[path] = desc
            
            # 부모 경로들도 추가
            parts = [p for p in path.split('\\') if p]
            for i in range(1, len(parts) + 1):
                partial_path = '\\' + '\\'.join(parts[:i])
                all_paths.add(partial_path)
        
        # 정렬
        sorted_paths = sorted(all_paths, key=lambda x: (x.count('\\'), x))
        
        print(f"총 {len(sorted_paths)}개 경로 삽입 시작...\n")
        
        for idx, path in enumerate(sorted_paths, 1):
            node_info = parse_path(path)
            
            if node_info:
                desc = path_descriptions.get(path, None)
                
                if insert_tree_node(cursor, node_info, desc):
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
        import traceback
        traceback.print_exc()
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
        
        # Description이 있는 노드 수
        cursor.execute("SELECT COUNT(*) as desc_count FROM tree_path_enum WHERE description IS NOT NULL AND description != ''")
        desc_count = cursor.fetchone()['desc_count']
        
        print(f"\n{'='*60}")
        print(f"📊 트리 통계")
        print(f"{'='*60}")
        print(f"전체 노드: {total}개")
        print(f"리프 노드: {leaf_count}개")
        print(f"브랜치 노드: {total - leaf_count}개")
        print(f"Description 있음: {desc_count}개")
        print(f"\n레벨별 분포:")
        for stat in level_stats:
            print(f"  Level {stat['node_level']}: {stat['count']}개")
        print(f"{'='*60}\n")
        
    except Error as e:
        print(f"❌ 통계 조회 오류: {e}")
    finally:
        cursor.close()

def show_sample_data(conn, limit=10):
    """샘플 데이터 조회"""
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT full_path, node_name, node_level, description 
            FROM tree_path_enum 
            WHERE description IS NOT NULL
            ORDER BY full_path 
            LIMIT %s
        """, (limit,))
        
        rows = cursor.fetchall()
        
        print(f"\n{'='*60}")
        print(f"📋 샘플 데이터 (Description 있는 노드)")
        print(f"{'='*60}")
        for row in rows:
            print(f"경로: {row['full_path']}")
            print(f"이름: {row['node_name']}")
            print(f"레벨: {row['node_level']}")
            print(f"설명: {row['description']}")
            print(f"{'-'*60}")
        
    except Error as e:
        print(f"❌ 샘플 조회 오류: {e}")
    finally:
        cursor.close()

# =====================================================
# 메인 실행
# =====================================================

if __name__ == '__main__':
    import sys
    csv_file = 'D:\hull3dviewer\MakeTree\data.csv'
    # 사용법 안내
    if len(sys.argv) < 2:
        print("="*60)
        print("사용법:")
        print("  python3 insert_tree_data_csv.py <csv_file_path>")
        print("\nCSV 형식:")
        print("  /path/to/node,Description text")
        print("\n예시:")
        print("  python3 insert_tree_data_csv.py tree_data.csv")
        print("="*60)
        sample_data = None
        # 샘플 데이터로 테스트
        print("\n샘플 데이터로 테스트 실행...")
        # sample_data = [
        #     ('/AYF201/A110B/F210C/F201_DK3-1SP', 'HPLATE idsp 2001 of HPANEL /F201_DK3'),
        #     ('/AYF201/A110B/F210C/F201_DK3-2SP', 'HPLATE idsp 2002 of HPANEL /F201_DK3'),
        #     ('/AYF201/A110B/F210C/F201_DK3-3SP', 'HPLATE idsp 2003 of HPANEL /F201_DK3'),
        # ]
    else:
        csv_file = 'data.csv'
        # csv_file = sys.argv[1]
        sample_data = None
    
    # DB 연결
    connection = create_connection()
    
    if connection and connection.is_connected():
        try:
            # if sample_data:
            #     # 샘플 데이터로 테스트
            #     insert_tree_data_from_list(connection, sample_data)
            # else:
                # CSV 파일에서 읽기
            insert_tree_data_from_csv(connection, csv_file)
            
            # 통계 조회
            get_tree_statistics(connection)
            
            # 샘플 데이터 표시
            show_sample_data(connection, 5)
            
        finally:
            connection.close()
            print("✅ DB 연결 종료")
    else:
        print("❌ DB 연결 실패")