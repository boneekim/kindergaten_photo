import os
import cv2
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import shutil
import tempfile
import streamlit as st
import io

def get_image_date(image_path):
    """
    이미지 파일에서 촬영 날짜를 추출하는 함수
    EXIF 데이터에서 날짜를 먼저 시도하고, 없으면 파일 생성 날짜 사용
    """
    try:
        # EXIF 데이터에서 날짜 추출 시도
        image = Image.open(image_path)
        exifdata = image.getexif()
        
        for tag_id in exifdata:
            tag = TAGS.get(tag_id, tag_id)
            data = exifdata.get(tag_id)
            
            if tag == "DateTime":
                return datetime.strptime(data, "%Y:%m:%d %H:%M:%S")
            elif tag == "DateTimeOriginal":
                return datetime.strptime(data, "%Y:%m:%d %H:%M:%S")
            elif tag == "DateTimeDigitized":
                return datetime.strptime(data, "%Y:%m:%d %H:%M:%S")
    except Exception as e:
        pass
    
    # EXIF 데이터가 없으면 파일 생성 날짜 사용
    try:
        timestamp = os.path.getctime(image_path)
        return datetime.fromtimestamp(timestamp)
    except Exception:
        return datetime.now()

def get_week_range(date):
    """
    주어진 날짜의 주차 범위를 계산하는 함수 (월요일 시작)
    """
    # 월요일을 주의 시작으로 설정
    start_of_week = date - timedelta(days=date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    year = start_of_week.year
    start_str = start_of_week.strftime("%m-%d")
    end_str = end_of_week.strftime("%d")
    
    # YY(MM-DD ~ DD) 형식으로 폴더명 생성
    folder_name = f"{year % 100:02d}({start_str} ~ {end_str})"
    
    return folder_name, start_of_week, end_of_week

def organize_photos_by_week(uploaded_files, output_dir):
    """
    업로드된 사진들을 주차별로 정리하는 함수
    """
    result_folders = {}
    
    # 각 이미지 파일 처리
    for uploaded_file in uploaded_files:
        if uploaded_file.type.startswith('image/'):
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            # 이미지 날짜 추출
            image_date = get_image_date(tmp_path)
            folder_name, start_date, end_date = get_week_range(image_date)
            
            # 폴더 경로 생성
            folder_path = os.path.join(output_dir, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            # 파일 복사
            dest_path = os.path.join(folder_path, uploaded_file.name)
            shutil.copy2(tmp_path, dest_path)
            
            # 결과 기록
            if folder_name not in result_folders:
                result_folders[folder_name] = []
            result_folders[folder_name].append(uploaded_file.name)
            
            # 임시 파일 삭제
            os.unlink(tmp_path)
    
    return result_folders

def create_slideshow_video(uploaded_files, output_dir):
    """
    업로드된 사진들로 슬라이드쇼 비디오를 생성하는 함수
    """
    # 이미지 파일들을 날짜순으로 정렬
    image_files_with_dates = []
    temp_files = []
    
    for uploaded_file in uploaded_files:
        if uploaded_file.type.startswith('image/'):
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
                temp_files.append(tmp_path)
            
            # 이미지 날짜 추출
            image_date = get_image_date(tmp_path)
            image_files_with_dates.append((tmp_path, image_date, uploaded_file.name))
    
    # 날짜순으로 정렬
    image_files_with_dates.sort(key=lambda x: x[1])
    
    if not image_files_with_dates:
        return None, "이미지 파일이 없습니다."
    
    # 비디오 파일명 생성 (첫 번째와 마지막 이미지의 날짜 범위)
    first_date = image_files_with_dates[0][1]
    last_date = image_files_with_dates[-1][1]
    
    # 주차 범위로 파일명 생성
    if first_date.isocalendar()[1] == last_date.isocalendar()[1]:
        # 같은 주차인 경우
        folder_name, _, _ = get_week_range(first_date)
    else:
        # 다른 주차인 경우 전체 범위 표시
        start_str = first_date.strftime("%m-%d")
        end_str = last_date.strftime("%m-%d")
        folder_name = f"{first_date.year % 100:02d}({start_str} ~ {end_str})"
    
    video_filename = f"{folder_name}.mov"
    video_path = os.path.join(output_dir, video_filename)
    
    try:
        # 첫 번째 이미지로 비디오 크기 결정
        first_image = cv2.imread(image_files_with_dates[0][0])
        if first_image is None:
            return None, "첫 번째 이미지를 읽을 수 없습니다."
            
        height, width, layers = first_image.shape
        
        # 비디오 코덱 설정 (MOV 파일용) - 더 호환성 높은 코덱 사용
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 0.5  # 2초당 1프레임 (한 장당 2초)
        
        # 비디오 라이터 생성
        video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
        
        if not video_writer.isOpened():
            return None, "비디오 라이터를 초기화할 수 없습니다."
        
        # 각 이미지를 비디오에 추가
        processed_count = 0
        for img_path, _, _ in image_files_with_dates:
            img = cv2.imread(img_path)
            if img is not None:
                # 크기 조정 (필요한 경우)
                img_resized = cv2.resize(img, (width, height))
                video_writer.write(img_resized)
                processed_count += 1
        
        # 비디오 라이터 안전하게 닫기
        video_writer.release()
        
        # 임시 파일들 삭제
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        if processed_count == 0:
            return None, "처리된 이미지가 없습니다."
        
        # 생성된 파일 확인
        if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
            return video_path, f"비디오가 성공적으로 생성되었습니다: {video_filename} ({processed_count}개 이미지 처리)"
        else:
            return None, "비디오 파일이 제대로 생성되지 않았습니다."
    
    except Exception as e:
        # 임시 파일들 삭제
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return None, f"비디오 생성 중 오류가 발생했습니다: {str(e)}"

def get_desktop_path():
    """
    사용자 데스크톱 경로를 반환하는 함수
    """
    return os.path.join(os.path.expanduser("~"), "Desktop")

def create_zip_file(folder_path, zip_path):
    """
    폴더를 ZIP 파일로 압축하는 함수
    """
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

def create_zip_buffer(folder_path):
    """
    폴더를 메모리 버퍼에 ZIP으로 압축하는 함수 (클라우드 환경용)
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # 상대 경로 생성 (유치원_사진_정리 폴더를 포함하도록)
                arcname = os.path.relpath(file_path, os.path.dirname(folder_path))
                zipf.write(file_path, arcname)
    
    zip_buffer.seek(0)
    return zip_buffer 