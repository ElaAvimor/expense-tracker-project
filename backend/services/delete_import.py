from sqlalchemy.orm import Session

from db.models import Import, Transaction


def delete_import_and_related_transactions(import_id: int, db: Session) -> bool:
    """
    Deletes an import and all associated transactions
    :param import_id: The unique hash of the import to delete
    :param db: The session through which we connect to the db
    :return: True if deletion was successful, False if import was not found
    """
    import_query = db.query(Import).filter(Import.id == import_id).first()
    if not import_query:
        return False

    db.query(Transaction).filter(Transaction.import_id == import_id).delete()
    db.delete(import_query)
    db.commit()

    return True
