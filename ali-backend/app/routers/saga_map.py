"""
Saga Map Router
Spec v2.2 §4.3: CourseManifest hierarchy API endpoints.

Provides endpoints for:
- GET /courses - List all courses with modules
- GET /courses/{course_id} - Get single course with modules
- GET /modules/{module_id}/status - Check unlock status for user
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import verify_token
from app.services.saga_map_service import get_saga_map_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/courses")
async def list_courses(
    status: Optional[str] = Query(default=None, description="Filter by status (ACTIVE, DRAFT)"),
    user: dict = Depends(verify_token)
):
    """
    List all courses with their modules.
    
    Returns course hierarchy with:
    - Course metadata
    - Nested modules (ordered by sequence)
    - User's progress for each module
    """
    user_id = user.get("uid")
    
    try:
        service = get_saga_map_service()
        
        # Get all courses (optionally filtered by status)
        courses = service.list_courses(status=status)
        
        # Enrich with modules and user progress
        result = []
        for course in courses:
            course_id = course.get("id")
            
            # Get modules for this course
            modules = service.list_modules_for_course(course_id)
            
            # Enrich each module with unlock status and progress
            enriched_modules = []
            for module in modules:
                module_id = module.get("id")
                
                # Check unlock status
                unlock_status = service.check_unlock_conditions(user_id, module_id)
                
                # Calculate progress
                progress = service.calculate_module_progress(user_id, module_id)
                
                completed_ids = progress.get("completedTutorialIds", [])
                enriched_modules.append({
                    **module,
                    "is_unlocked": unlock_status.get("isUnlocked", True),
                    "unlock_reason": unlock_status.get("reason"),
                    "progress_percent": progress.get("percentComplete", 0),
                    "completed_tutorials": len(completed_ids),
                    "total_tutorials": progress.get("totalTutorials", 0)
                })
            
            # Calculate course-level progress
            course_progress = service.calculate_course_progress(user_id, course_id)
            completed_modules = sum(
                1 for module in enriched_modules if module.get("progress_percent", 0) >= 100
            )
            
            result.append({
                **course,
                "modules": enriched_modules,
                "progress_percent": course_progress.get("percentComplete", 0),
                "completed_modules": completed_modules,
                "total_modules": len(enriched_modules)
            })
        
        logger.info(f"📚 Listed {len(result)} courses for user {user_id}")
        return {"courses": result}
        
    except Exception as e:
        logger.error(f"❌ Failed to list courses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch courses: {str(e)}")


@router.get("/courses/{course_id}")
async def get_course(
    course_id: str,
    user: dict = Depends(verify_token)
):
    """
    Get a single course with all its modules and user progress.
    """
    user_id = user.get("uid")
    
    try:
        service = get_saga_map_service()
        
        course = service.get_course(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        modules = service.list_modules_for_course(course_id)
        
        enriched_modules = []
        for module in modules:
            module_id = module.get("id")
            unlock_status = service.check_unlock_conditions(user_id, module_id)
            progress = service.calculate_module_progress(user_id, module_id)
            
            enriched_modules.append({
                **module,
                "is_unlocked": unlock_status.get("isUnlocked", True),
                "unlock_reason": unlock_status.get("reason"),
                "progress_percent": progress.get("percentComplete", 0)
            })
        
        course_progress = service.calculate_course_progress(user_id, course_id)
        
        return {
            **course,
            "modules": enriched_modules,
            "progress_percent": course_progress.get("percentComplete", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get course {course_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modules/{module_id}/status")
async def get_module_status(
    module_id: str,
    user: dict = Depends(verify_token)
):
    """
    Check unlock status and progress for a specific module.
    """
    user_id = user.get("uid")
    
    try:
        service = get_saga_map_service()
        
        module = service.get_module(module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        unlock_status = service.check_unlock_conditions(user_id, module_id)
        progress = service.calculate_module_progress(user_id, module_id)
        
        completed_ids = progress.get("completedTutorialIds", [])
        return {
            "module_id": module_id,
            "title": module.get("title"),
            "is_unlocked": unlock_status.get("isUnlocked", True),
            "unlock_reason": unlock_status.get("reason"),
            "progress_percent": progress.get("percentComplete", 0),
            "completed_tutorials": len(completed_ids),
            "total_tutorials": progress.get("totalTutorials", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get module status {module_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
