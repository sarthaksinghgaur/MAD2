from flask import jsonify, request, session, make_response
from flask_restful import Resource
from flask_security import auth_token_required, roles_accepted, roles_required
from models import User, Campaign, AdRequest, Sponsor, Influencer, db
from cacher import cache

class AdminDashboard(Resource):
    @auth_token_required
    @roles_accepted('admin')
    @cache.cached(timeout=10)
    def get(self):
        active_users = User.query.filter_by(active=True).count()
        total_campaigns = Campaign.query.count()
        public_campaigns = Campaign.query.filter_by(visibility='public').count()
        private_campaigns = Campaign.query.filter_by(visibility='private').count()
        ad_requests = AdRequest.query.count()
        flagged_sponsors = Sponsor.query.filter_by(flagged=True).count()
        flagged_influencers = Influencer.query.filter_by(flagged=True).count()
        flagged_campaigns = Campaign.query.filter_by(flagged=True).count()
        flagged_ad_requests = AdRequest.query.filter_by(flagged=True).count()

        pending_ad_requests = AdRequest.query.filter(
            AdRequest.status.in_(['Negotiations Underway from Sponsor', 'Negotiations Underway from Influencer', 'Influencer Requested for Ad'])
        ).count()
        accepted_ad_requests = AdRequest.query.filter_by(status='Accepted').count()

        stats = {
            'active_users': active_users,
            'total_campaigns': total_campaigns,
            'public_campaigns': public_campaigns,
            'private_campaigns': private_campaigns,
            'ad_requests': ad_requests,
            'flagged_sponsors': flagged_sponsors,
            'flagged_influencers': flagged_influencers,
            'flagged_campaigns': flagged_campaigns,
            'flagged_ad_requests': flagged_ad_requests,
            'pending_ad_requests': pending_ad_requests,
            'accepted_ad_requests': accepted_ad_requests
        }

        return jsonify({'stats': stats })

class PendingSponsors(Resource):
    @auth_token_required
    @roles_required('admin')
    def get(self):
        pending_sponsors = Sponsor.query.filter_by(is_approved=False).all()
        sponsors_data = [
            {
                "id": sponsor.id,
                "company_name": sponsor.company_name,
                "industry": sponsor.industry,
                "budget": sponsor.budget
            }
            for sponsor in pending_sponsors
        ]
        return make_response(jsonify({"pending_sponsors": sponsors_data}), 200)

class ApproveSponsor(Resource):
    @auth_token_required
    @roles_required('admin')
    def post(self, sponsor_id):
        sponsor = Sponsor.query.filter_by(id=sponsor_id, is_approved=False).first()
        if not sponsor:
            return make_response(jsonify({"message": "Sponsor not found or already approved"}), 404)
        
        sponsor.is_approved = True
        db.session.commit()
        cache.clear()
        
        return make_response(jsonify({"message": "Sponsor has been approved", "username": sponsor.company_name}), 200)

class AdminViewUsers(Resource):
    @auth_token_required
    @roles_accepted('admin')
    @cache.cached(timeout=10)
    def get(self):
        users = User.query.all()
        users_data = [{'id': user.id, 'username': user.username, 'email': user.email} for user in users]
        return jsonify(users_data)

class ToggleUserActive(Resource):
    @auth_token_required
    @roles_required('admin')
    def post(self, user_id):
        data = request.get_json()
        if not data or 'active' not in data:
            return make_response(jsonify({"message": "Invalid request. 'active' field is required."}), 400)

        active_status = data['active']
        
        user = User.query.get(user_id)
        if not user:
            return make_response(jsonify({"message": "User not found."}), 404)

        user.active = active_status
        db.session.commit()
        cache.clear()

        status_text = "activated" if user.active else "deactivated"
        return make_response(jsonify({"message": f"User has been {status_text} successfully.", "user_id": user.id, "active": user.active}), 200)



class AdminViewCampaigns(Resource):
    @auth_token_required
    @roles_accepted('admin')
    @cache.cached(timeout=10)
    def get(self):
        campaigns = Campaign.query.all()
        campaigns_data = [
            {
                'id': campaign.id,
                'name': campaign.name,
                'description': campaign.description,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'budget': campaign.budget,
                'visibility': campaign.visibility,
                'goals': campaign.goals,
                'flagged': campaign.flagged
            } 
            for campaign in campaigns
        ]
        return jsonify(campaigns_data)


class AdminViewAdRequests(Resource):
    @auth_token_required
    @roles_accepted('admin')
    @cache.cached(timeout=10)
    def get(self):
        ad_requests = AdRequest.query.all()
        ad_requests_data = [
            {
                'id': ad_request.id,
                'name': ad_request.name,
                'messages': ad_request.messages,
                'requirements': ad_request.requirements,
                'payment_amount': ad_request.payment_amount,
                'status': ad_request.status,
                'flagged': ad_request.flagged
            } 
            for ad_request in ad_requests
        ]
        return jsonify(ad_requests_data)

    
class AdminViewSponsors(Resource):
    @auth_token_required
    @roles_accepted('admin')
    @cache.cached(timeout=10)
    def get(self):
        sponsors = Sponsor.query.all()
        sponsors_data = [
            {
                'id': sponsor.id,
                'company_name': sponsor.company_name,
                'industry': sponsor.industry,
                'budget': sponsor.budget,
                'flagged': sponsor.flagged
            } 
            for sponsor in sponsors
        ]
        return jsonify(sponsors_data)

    
class AdminViewInfluencers(Resource):
    @auth_token_required
    @roles_accepted('admin')
    @cache.cached(timeout=10)
    def get(self):
        influencers = Influencer.query.all()
        influencers_data = [
            {
                'id': influencer.id,
                'name': influencer.name,
                'category': influencer.category,
                'niche': influencer.niche,
                'reach': influencer.reach,
                'platform': influencer.platform,
                'flagged': influencer.flagged
            } 
            for influencer in influencers
        ]
        return jsonify(influencers_data)
    
class FlagCampaign(Resource):
    @auth_token_required
    @roles_required('admin')
    def post(self, campaign_id):
        campaign = Campaign.query.get(campaign_id)

        if not campaign:
            return jsonify({"message": "Campaign not found"})
        
        campaign.flagged = not campaign.flagged
        db.session.commit()
        cache.clear()

        status = "flagged" if campaign.flagged else "unflagged"
        return jsonify({"message": f"Campaign has been {status}.", "campaign_id": campaign.id, "flagged": campaign.flagged})
    
class FlagSponsor(Resource):
    @auth_token_required
    @roles_required('admin')
    def post(self, sponsor_id):
        sponsor = Sponsor.query.get(sponsor_id)

        if not sponsor:
            return jsonify({"message": "Sponsor not found"}), 404
        
        sponsor.flagged = not sponsor.flagged
        db.session.commit()
        cache.clear()
        
        status = "flagged" if sponsor.flagged else "unflagged"
        return jsonify({"message": f"Sponsor has been {status}.", "sponsor_id": sponsor.id, "flagged": sponsor.flagged})

    
class FlagInfluencer(Resource):
    @roles_required('admin')
    @auth_token_required
    def post(self, influencer_id):

        influencer = Influencer.query.get(influencer_id)
        if not influencer:
            return jsonify({"message": "Influencer not found"}), 404

        influencer.flagged = not influencer.flagged
        db.session.commit()
        cache.clear()
        
        status = "flagged" if influencer.flagged else "unflagged"
        return jsonify({"message": f"Influencer has been {status}.", "influencer_id": influencer.id, "flagged": influencer.flagged})
    

class FlagAdRequest(Resource):
    @auth_token_required
    @roles_required('admin')
    def post(self, ad_request_id):
        ad_request = AdRequest.query.get(ad_request_id)
        if not ad_request:
            return jsonify({"message": "Ad request not found"}), 404

        ad_request.flagged = not ad_request.flagged
        db.session.commit()
        cache.clear()

        status = "flagged" if ad_request.flagged else "unflagged"
        return jsonify({"message": f"Ad request has been {status}.", "ad_request_id": ad_request.id, "flagged": ad_request.flagged})
    