python main.py --project_dir hypertune --dataset Bios_gender --emb_size 768 --num_classes 28 --batch_size 512 --learning_rate 0.01 --hidden_size 200 --n_hidden 1 --dropout 0.0 --base_seed 1 --exp_id hypertune_vanilla0
sleep 2
python main.py --project_dir hypertune --dataset Bios_gender --emb_size 768 --num_classes 28 --batch_size 512 --learning_rate 0.01 --hidden_size 200 --n_hidden 1 --dropout 0.0 --batch_norm --base_seed 1 --exp_id hypertune_vanilla1