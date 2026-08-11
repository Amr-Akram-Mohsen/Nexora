from app.core.extensions import db
from app.domains.interaction.models import Save
from app.domains.interaction.service.command import execute_counter_update
def rename_collection(user, old_name: str, new_name: str):
    old_name = old_name.strip().lower()
    new_name = new_name.strip().lower()
    if not new_name or old_name == new_name:
        return {'success': False, 'error': 'Invalid collection name'}
    saves = Save.query.filter_by(user_id=user.id, collection_name=old_name).all()
    for save in saves:
        existing = Save.query.filter_by(user_id=user.id, target_type=save.target_type, target_id=save.target_id, collection_name=new_name).first()
        if existing:
            db.session.delete(save)
        else:
            save.collection_name = new_name
    db.session.commit()
    return {'success': True}
def delete_collection(user, collection_name: str, move_to_global: bool=False):
    collection_name = collection_name.strip().lower()
    saves = Save.query.filter_by(user_id=user.id, collection_name=collection_name).all()
    for save in saves:
        if move_to_global:
            existing = Save.query.filter_by(user_id=user.id, target_type=save.target_type, target_id=save.target_id, collection_name='general').first()
            if existing:
                db.session.delete(save)
            else:
                save.collection_name = 'general'
        else:
            db.session.delete(save)
            execute_counter_update(db=db, model_type=save.target_type, model_id=save.target_id, column='save_count', action='dec')
    db.session.commit()
    return {'success': True}
def move_save_collection(user, target_type: str, target_id: int, new_collection_name: str, old_collection_name: str=None):
    new_collection_name = (new_collection_name or 'general').strip().lower()
    query = Save.query.filter_by(user_id=user.id, target_type=target_type, target_id=target_id)
    if old_collection_name:
        query = query.filter_by(collection_name=old_collection_name.strip().lower())
    save = query.first()
    if not save:
        return {'success': False, 'error': 'Save not found'}
    if save.collection_name == new_collection_name:
        return {'success': True}
    existing = Save.query.filter_by(user_id=user.id, target_type=target_type, target_id=target_id, collection_name=new_collection_name).first()
    if existing:
        db.session.delete(save)
    else:
        save.collection_name = new_collection_name
    db.session.commit()
    return {'success': True}