-- sql/user.sql

-- name: create_user
INSERT INTO t_user (id, name, address, sex)
VALUES (:id, :name, :address, :sex);

-- name: get_user_by_id
SELECT id, name, address, sex
FROM t_user
WHERE id = :user_id;

-- name: get_all_users
SELECT id, name, address, sex
FROM t_user
LIMIT :limit OFFSET :offset;

-- name: update_user
UPDATE t_user SET
    name = COALESCE(:name, name),
    address = COALESCE(:address, address),
    sex = COALESCE(:sex, sex)
WHERE id = :id;

-- name: delete_user
DELETE FROM t_user WHERE id = :id;