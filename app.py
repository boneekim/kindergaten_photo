import streamlit as st
import os
import tempfile
import shutil
from pathlib import Path
from utils import (
    organize_photos_by_week, 
    create_slideshow_video, 
    get_desktop_path,
    create_zip_file,
    create_zip_buffer
)

def main():
    st.set_page_config(
        page_title="유치원 사진 정리 프로그램",
        page_icon="📸",
        layout="wide"
    )
    
    # 타이틀과 설명
    st.title("📸 유치원 사진 정리 프로그램")
    st.markdown("---")
    st.markdown("""
    **사진들을 업로드하고 원하는 방식으로 정리해보세요!**
    
    - 📁 **날짜별로 폴더 취합**: 촬영 날짜 기준으로 주차별 폴더로 정리
    - 🎬 **하나의 영상으로 제작**: 날짜순으로 정렬하여 슬라이드쇼 비디오 생성
    """)
    
    # 파일 업로더
    st.markdown("### 📤 사진 업로드")
    uploaded_files = st.file_uploader(
        "여러 장의 사진을 선택해주세요",
        type=['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
        accept_multiple_files=True,
        help="JPG, JPEG, PNG, BMP, TIFF 형식의 이미지 파일을 지원합니다."
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)}개의 사진이 업로드되었습니다.")
        
        # 업로드된 파일 미리보기
        with st.expander("📋 업로드된 파일 목록 보기"):
            for i, file in enumerate(uploaded_files, 1):
                st.write(f"{i}. {file.name} ({file.size} bytes)")
    
    # 처리 옵션 선택
    st.markdown("### ⚙️ 처리 방식 선택")
    
    col1, col2 = st.columns(2)
    
    with col1:
        option1 = st.button(
            "📁 날짜별로 폴더 취합",
            help="촬영 날짜를 기준으로 주차별 폴더를 만들어 사진들을 정리합니다.",
            use_container_width=True,
            type="primary"
        )
    
    with col2:
        option2 = st.button(
            "🎬 하나의 영상으로 제작",
            help="사진들을 날짜순으로 정렬하여 슬라이드쇼 비디오로 만듭니다.",
            use_container_width=True,
            type="secondary"
        )
    
    # 결과 출력 영역
    st.markdown("### 📊 처리 결과")
    
    if uploaded_files:
        if option1:
            process_folder_organization(uploaded_files)
        elif option2:
            process_video_creation(uploaded_files)
    else:
        if option1 or option2:
            st.warning("⚠️ 먼저 사진을 업로드해주세요.")

def process_folder_organization(uploaded_files):
    """날짜별 폴더 정리 처리"""
    
    with st.spinner("📁 날짜별 폴더로 정리 중..."):
        try:
            # 임시 디렉토리에 폴더 생성 (클라우드 환경 호환)
            with tempfile.TemporaryDirectory() as temp_dir:
                output_base = os.path.join(temp_dir, "유치원_사진_정리")
                os.makedirs(output_base, exist_ok=True)
                
                # 사진들을 주차별로 정리
                result_folders = organize_photos_by_week(uploaded_files, output_base)
                
                if result_folders:
                    st.success("✅ 사진 정리가 완료되었습니다!")
                    
                    # 결과 표시
                    st.markdown("#### 📂 생성된 폴더 구조")
                    
                    for folder_name, files in result_folders.items():
                        with st.expander(f"📁 {folder_name} ({len(files)}개 파일)"):
                            for file in files:
                                st.write(f"• {file}")
                    
                    # 폴더 정보 표시
                    st.info(f"📍 폴더가 생성되었습니다. 아래 ZIP 파일을 다운로드하여 확인하세요.")
                    
                    # ZIP 파일 생성
                    zip_buffer = create_zip_buffer(output_base)
                    
                    # ZIP 파일 다운로드 제공
                    st.download_button(
                        label="📦 ZIP 파일로 다운로드",
                        data=zip_buffer.getvalue(),
                        file_name="유치원_사진_정리.zip",
                        mime="application/zip",
                        help="다운로드한 ZIP 파일을 압축 해제하면 주차별로 정리된 폴더들을 볼 수 있습니다."
                    )
                    
                    # 폴더 구조 미리보기
                    st.markdown("#### 📋 폴더 구조 미리보기")
                    st.code(f"""
유치원_사진_정리/
{chr(10).join([f"├── {folder}/ ({len(files)}개 파일)" for folder, files in result_folders.items()])}
                    """)
                    
                else:
                    st.error("❌ 처리할 이미지 파일이 없습니다.")
                
        except Exception as e:
            st.error(f"❌ 처리 중 오류가 발생했습니다: {str(e)}")
            st.error(f"상세 오류: {type(e).__name__}")

def process_video_creation(uploaded_files):
    """슬라이드쇼 비디오 생성 처리"""
    
    with st.spinner("🎬 슬라이드쇼 비디오 생성 중... (시간이 좀 걸릴 수 있습니다)"):
        try:
            # 임시 디렉토리에서 비디오 생성 (클라우드 환경 호환)
            with tempfile.TemporaryDirectory() as temp_dir:
                # 비디오 생성
                video_path, message = create_slideshow_video(uploaded_files, temp_dir)
                
                if video_path and os.path.exists(video_path):
                    st.success("✅ 슬라이드쇼 비디오가 생성되었습니다!")
                    
                    # 비디오 정보 표시
                    video_size = os.path.getsize(video_path)
                    video_name = os.path.basename(video_path)
                    
                    st.info(f"""
                    📹 **비디오 정보**
                    - 파일명: `{video_name}`
                    - 크기: {video_size / (1024*1024):.2f} MB
                    - 한 장당 2초씩 재생됩니다.
                    - 아래 버튼으로 다운로드하세요.
                    """)
                    
                    # 비디오 파일 다운로드 제공
                    with open(video_path, "rb") as video_file:
                        video_data = video_file.read()
                        st.download_button(
                            label="🎬 비디오 파일 다운로드",
                            data=video_data,
                            file_name=video_name,
                            mime="video/quicktime",
                            help="생성된 MOV 파일을 다운로드합니다."
                        )
                    
                    # 미리보기 (브라우저에서 지원하는 경우)
                    try:
                        st.markdown("#### 🎥 미리보기")
                        st.video(video_data)
                    except Exception:
                        st.info("💡 비디오 미리보기는 브라우저에서 지원하지 않을 수 있습니다. 다운로드하여 확인해주세요.")
                        
                else:
                    st.error(f"❌ {message}")
                
        except Exception as e:
            st.error(f"❌ 비디오 생성 중 오류가 발생했습니다: {str(e)}")
            st.error(f"상세 오류: {type(e).__name__}")

# 사이드바에 정보 추가
def add_sidebar():
    st.sidebar.title("📋 사용 가이드")
    st.sidebar.markdown("""
    ### 📸 지원 형식
    - JPG, JPEG, PNG, BMP, TIFF
    
    ### 📁 날짜별 폴더 정리
    - 사진의 EXIF 데이터에서 촬영 날짜 추출
    - 주차별로 폴더 생성 (월요일 시작)
    - 폴더명: `YY(MM-DD ~ DD)` 형식
    - ZIP 파일로 다운로드
    
    ### 🎬 슬라이드쇼 비디오
    - 날짜순으로 자동 정렬
    - 한 장당 2초 재생
    - MOV 형식으로 저장
    - 직접 다운로드 가능
    
    ### 💾 다운로드 방법
    - 처리 완료 후 다운로드 버튼 클릭
    - ZIP 파일 또는 MOV 파일로 저장
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**개발자**: Curser AI Assistant")
    st.sidebar.markdown("**버전**: 1.0.0")

if __name__ == "__main__":
    add_sidebar()
    main() 